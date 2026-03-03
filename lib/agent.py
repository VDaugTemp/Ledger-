# lib/agent.py
"""Deterministic controller-driven LangGraph pipeline.

Graph:  controller (deterministic) → [retrieve?] → answer (LLM) → critic → END
"""
from __future__ import annotations

import asyncio
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Optional

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_qdrant import QdrantVectorStore
from langgraph.checkpoint.redis import AsyncRedisSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from qdrant_client import QdrantClient
from typing_extensions import TypedDict

from lib.deterministic_tools import (
    apply_profile_patch,
    consistency_checker,
    filing_form_selector,
    intent_classifier,
    next_question,
    parse_answer_for_field,
    presence_calculator,
)
from lib.model_provider import ModelProviderChatModel, ModelProviderEmbeddings

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / ".env.local", override=True)

# ── Vector store (lazy init) ──────────────────────────────────────────────────
_qdrant_client: Optional[QdrantClient] = None
_vector_store: Optional[QdrantVectorStore] = None


def _get_vector_store() -> QdrantVectorStore:
    global _qdrant_client, _vector_store
    if _vector_store is None:
        _qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
        embeddings = ModelProviderEmbeddings(model="text-embedding-3-small")
        _vector_store = QdrantVectorStore(
            client=_qdrant_client,
            collection_name="malaysia-tax-laws",
            embedding=embeddings,
        )
    return _vector_store


# ── Graph state ───────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    profile: dict                   # full Profile JSON from frontend
    skipped_field_paths: list[str]
    today_iso: str
    task_packet: Optional[dict]
    retrieved_chunks: list[dict]
    profile_patch: Optional[dict]   # extracted by controller; emitted as SSE


# ── Answer node system prompt ─────────────────────────────────────────────────
_ANSWER_SYSTEM = """You are an expert Malaysian tax advisor for digital nomads and expats.

Rules:
- Never give definitive tax advice; qualify with "generally", "typically", "based on the rules".
- Cite document names, section numbers, or thresholds when stating rules.
- Answer the user's question FIRST.
- Then, if <next_question> appears in your context, ask it VERBATIM at the end.
- Ask AT MOST ONE question per response.
- No filler, padding, or repetition.

Banned phrases (replace with softer language if you catch yourself using them):
  "you should", "you definitely", "you don't need", "you are required to", "you must"
"""

# ── Controller node ───────────────────────────────────────────────────────────

def _build_profile_summary(profile: dict, decision_map: dict) -> str:
    income = profile.get("incomeTypes") or {}
    active = [k for k, v in income.items() if v]
    trips = (profile.get("presence") or {}).get("trips") or []
    year = profile.get("assessmentYear") or 2025
    jurisdiction = profile.get("jurisdiction") or "MY"

    lines = [
        f"Profile: {jurisdiction} | Year {year}",
        f"Income: {', '.join(active) if active else 'none declared'}",
        f"Trips: {len(trips)} logged",
    ]

    if trips:
        calc = presence_calculator(trips, year)
        lines.append(f"Days in jurisdiction: {calc['daysInYear']}")
        if calc["near183"]:
            lines.append("⚠️ At/above 183 days (likely tax resident)")
        elif calc["near60"]:
            lines.append("ℹ️ Near 60-day threshold")
        if calc["rolling12Months"] >= 182 and not calc["near183"]:
            lines.append(f"⚠️ Rolling 12-month: {calc['rolling12Months']} days — may exceed 183-day threshold")

    ctx = profile.get("advisorContext") or {}
    if ctx.get("visaType"):
        lines.append(f"Visa: {ctx['visaType']}")

    score = (profile.get("dataQuality") or {}).get("completenessScore") or 0
    lines.append(f"Profile completeness: {score}%")
    return "\n".join(lines)


def _build_flags(profile: dict, decision_map: dict) -> list[dict]:
    flags = []
    trips = (profile.get("presence") or {}).get("trips") or []
    year = profile.get("assessmentYear") or 2025
    days_in_year = 0
    if trips:
        calc = presence_calculator(trips, year)
        days_in_year = calc["daysInYear"]
        if calc["near183"]:
            flags.append({"code": "NEAR_183", "severity": "warn",
                          "message": f"{calc['daysInYear']} days — likely tax resident"})
        elif calc["near60"]:
            flags.append({"code": "NEAR_60", "severity": "info",
                          "message": f"{calc['daysInYear']} days — near 60-day threshold"})
        if calc["rolling12Months"] >= 182:
            flags.append({"code": "NEAR_183_ROLLING", "severity": "warn",
                          "message": f"{calc['rolling12Months']} days in rolling 12-month window — may trigger 183-day threshold"})
    if not decision_map.get("residencyDecidable"):
        flags.append({"code": "RESIDENCY_UNDECIDABLE", "severity": "info",
                      "message": "Cannot determine residency without complete trip data"})
    consistency = consistency_checker(profile, days_in_year)
    for item in consistency.get("contradictions", []):
        if item["severity"] == "high":
            flags.append(item)
    flags.extend(consistency.get("risk_flags", []))
    return flags


def controller_node(state: AgentState) -> dict:
    """Deterministic controller: classify intent, extract profile update, build TaskPacket."""
    messages = state["messages"]
    profile = dict(state.get("profile") or {})
    skipped = list(state.get("skipped_field_paths") or [])
    today_iso = state.get("today_iso") or datetime.now(timezone.utc).date().isoformat()

    last_human = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    raw_content = last_human.content if last_human else ""
    # HumanMessage.content can be str | list (multimodal); flatten to plain text
    if isinstance(raw_content, list):
        user_msg: str = " ".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in raw_content
        )
    else:
        user_msg = raw_content

    # 1. Classify intent
    intent = intent_classifier(user_msg)["intent"]

    # 2. Find next open question
    nq_result = next_question(profile, skipped)
    next_q = nq_result.get("nextQuestion")

    # 3. Extract profile update if PROFILE_INPUT
    profile_patch: Optional[dict] = None
    clarifier: Optional[str] = None

    if intent == "PROFILE_INPUT" and next_q:
        parse_result = parse_answer_for_field(next_q["fieldPath"], user_msg, today_iso)

        if parse_result.get("skip"):
            skipped = [*skipped, next_q["fieldPath"]]
            nq_result = next_question(profile, skipped)
            next_q = nq_result.get("nextQuestion")

        elif parse_result.get("confidenceTier") == "high":
            patch = parse_result.get("patch") or {}
            if patch:
                meta = {
                    "source": "chat",
                    "fieldPath": next_q["fieldPath"],
                    "questionId": next_q["id"],
                    "confidenceTier": "high",
                    "rawUserText": user_msg,
                    "timestampIso": datetime.now(timezone.utc).isoformat(),
                }
                profile = apply_profile_patch(profile, patch, meta)
                profile_patch = patch
                nq_result = next_question(profile, skipped)
                next_q = nq_result.get("nextQuestion")

        elif parse_result.get("confidenceTier") == "low":
            clarifier = parse_result.get("needsClarification")
            next_q = None  # Ask clarifier instead

    # 4. Build TaskPacket
    decision_map = nq_result.get("decisionMap") or {}
    flags = _build_flags(profile, dict(decision_map))
    profile_summary = _build_profile_summary(profile, dict(decision_map))

    # Compute suggested filing form
    trips = (profile.get("presence") or {}).get("trips") or []
    _year = profile.get("assessmentYear") or 2025
    _days = presence_calculator(trips, _year)["daysInYear"] if trips else 0
    suggested_form = filing_form_selector(profile, _days)

    retrieval_query: Optional[str] = None
    retrieval_filters: Optional[dict] = None
    if intent in ("INFO", "WHAT_IF"):
        retrieval_query = user_msg
        retrieval_filters = {"jurisdiction": profile.get("jurisdiction") or "MY"}
    elif next_q and intent == "PROFILE_INPUT":
        retrieval_query = f"Malaysia tax {next_q['fieldPath'].replace('.', ' ')}"
        retrieval_filters = {"jurisdiction": "MY"}

    effective_next_q = next_q
    if clarifier:
        effective_next_q = {"id": "clarifier", "fieldPath": "", "question": clarifier, "priority": 0}

    task_packet: dict = {
        "intent": intent,
        "nextQuestion": effective_next_q,
        "profileSummary": profile_summary,
        "retrievalQuery": retrieval_query,
        "retrievalFilters": retrieval_filters,
        "decisionMap": decision_map,
        "flags": flags,
        "suggestedForm": suggested_form,
    }

    return {
        "task_packet": task_packet,
        "profile": profile,
        "skipped_field_paths": skipped,
        "profile_patch": profile_patch,
        "retrieved_chunks": [],
    }


# ── Retrieve node ─────────────────────────────────────────────────────────────

async def retrieve_node(state: AgentState) -> dict:
    task_packet = state.get("task_packet") or {}
    query = task_packet.get("retrievalQuery")
    if not query:
        return {"retrieved_chunks": []}

    vs = _get_vector_store()
    retriever = vs.as_retriever(search_kwargs={"k": 5})
    try:
        docs = await retriever.ainvoke(query)
    except Exception as exc:
        print(f"[RETRIEVE] Error: {exc}")
        return {"retrieved_chunks": []}

    chunks = []
    for doc in docs:
        meta = doc.metadata
        chunks.append({
            "chunkId": meta.get("chunk_id", str(uuid.uuid4())),
            "text": doc.page_content,
            "sectionRef": meta.get("reference", ""),
            "sourceTitle": meta.get("title", ""),
            "sourceUrl": meta.get("url", ""),
        })
    return {"retrieved_chunks": chunks}


# ── Answer node ───────────────────────────────────────────────────────────────

async def answer_node(state: AgentState) -> dict:
    messages = state["messages"]
    task_packet = state.get("task_packet") or {}
    chunks = state.get("retrieved_chunks") or []

    context_parts: list[str] = []

    profile_summary = task_packet.get("profileSummary") or ""
    if profile_summary:
        context_parts.append(f"<profile_context>\n{profile_summary}\n</profile_context>")

    dm = task_packet.get("decisionMap") or {}
    if dm:
        context_parts.append(
            f"<decision_map>"
            f"residency_decidable={dm.get('residencyDecidable')}, "
            f"income_scope_decidable={dm.get('incomeScopeDecidable')}, "
            f"dta_decidable={dm.get('dtaDecidable')}, "
            f"fsi_decidable={dm.get('fsiDecidable')}"
            f"</decision_map>"
        )

    flags = task_packet.get("flags") or []
    if flags:
        flag_lines = "\n".join(f"- [{f['severity'].upper()}] {f['message']}" for f in flags)
        context_parts.append(f"<flags>\n{flag_lines}\n</flags>")

    if chunks:
        chunk_texts = [
            f"[{c.get('sectionRef') or c.get('sourceTitle') or 'Unknown'}]\n{c['text']}"
            for c in chunks
        ]
        context_parts.append(f"<retrieved_context>\n{'---'.join(chunk_texts)}\n</retrieved_context>")

    suggested_form = task_packet.get("suggestedForm") or {}
    if suggested_form.get("decidable") and suggested_form.get("form"):
        context_parts.append(
            f"<suggested_form>{suggested_form['form']} — {suggested_form['reason']}</suggested_form>"
        )

    next_q = task_packet.get("nextQuestion")
    if next_q:
        context_parts.append(
            f"<next_question>\n"
            f"After answering the user, ask this question verbatim:\n"
            f"\"{next_q['question']}\"\n"
            f"</next_question>"
        )

    llm_messages: list = [SystemMessage(content=_ANSWER_SYSTEM)]
    if context_parts:
        llm_messages.append(SystemMessage(content="\n\n".join(context_parts)))
    # Last 10 messages (skip empty AI messages)
    history = [m for m in messages[-10:] if not isinstance(m, AIMessage) or m.content]
    llm_messages.extend(history)

    model = ModelProviderChatModel(timeout=60)
    response = await model.ainvoke(llm_messages)
    return {"messages": [response]}


# ── Critic node ───────────────────────────────────────────────────────────────

_SOFTENING: dict[str, str] = {
    "you should": "you may want to",
    "definitely": "generally",
    "you don't need": "you may not need",
    "you are required to": "it's generally required that",
    "you must": "it's typically the case that you must",
}


def critic_node(state: AgentState) -> dict:
    messages = state["messages"]
    last_ai = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
    if not last_ai:
        return {}

    # Ensure text is a string (AIMessage.content can be str or list)
    if isinstance(last_ai.content, list):
        text = " ".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in last_ai.content)
    else:
        text = last_ai.content
    
    modified = False
    for phrase, replacement in _SOFTENING.items():
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        new_text, count = pattern.subn(replacement, text)
        if count:
            text = new_text
            modified = True

    # Warn if >2 question marks (for monitoring)
    q_count = len(re.findall(r"\?(?!\s*[\]\)])", text))
    if q_count > 1:
        print(f"[CRITIC] Warning: {q_count} question marks in response")

    if modified:
        updated = AIMessage(content=text)
        new_msgs = []
        replaced = False
        for m in reversed(messages):
            if not replaced and isinstance(m, AIMessage):
                new_msgs.insert(0, updated)
                replaced = True
            else:
                new_msgs.insert(0, m)
        return {"messages": new_msgs}

    return {}


# ── Graph routing ─────────────────────────────────────────────────────────────

def _should_retrieve(state: AgentState) -> str:
    tp = state.get("task_packet") or {}
    return "retrieve" if tp.get("retrievalQuery") else "answer"


# ── Graph assembly ────────────────────────────────────────────────────────────

_graph = None
_graph_lock: asyncio.Lock | None = None


def _get_graph_lock() -> asyncio.Lock:
    global _graph_lock
    if _graph_lock is None:
        _graph_lock = asyncio.Lock()
    return _graph_lock


async def get_graph():
    global _graph
    async with _get_graph_lock():
        if _graph is None:
            redis_url = (os.getenv("REDIS_URL") or "").strip()
            if not redis_url:
                raise ValueError("REDIS_URL is not set")
            if not redis_url.startswith(("redis://", "rediss://", "unix://")):
                redis_url = "redis://" + redis_url

            checkpointer = AsyncRedisSaver(redis_url=redis_url, checkpoint_prefix="tax-agent-v2")
            await checkpointer.asetup()

            builder = StateGraph(AgentState)
            builder.add_node("controller", controller_node)
            builder.add_node("retrieve", retrieve_node)
            builder.add_node("answer", answer_node)
            builder.add_node("critic", critic_node)

            builder.set_entry_point("controller")
            builder.add_conditional_edges("controller", _should_retrieve,
                                          {"retrieve": "retrieve", "answer": "answer"})
            builder.add_edge("retrieve", "answer")
            builder.add_edge("answer", "critic")
            builder.add_edge("critic", END)

            _graph = builder.compile(checkpointer=checkpointer)

    return _graph
