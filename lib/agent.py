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
    freshness_requested as detect_freshness,
    intent_classifier,
    next_question,
    parse_answer_for_field,
    presence_calculator,
    topic_classifier,
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
    # Tavily-related fields
    freshness_requested: bool
    topic: str                          # "DTA_COUNTRY_LIST" | "PUBLIC_RULING_UPDATE" | "FILING_DEADLINE_CHANGE" | "OTHER"
    max_qdrant_score: float
    tavily_triggered: bool
    tavily_reason: Optional[str]        # "freshnessRequested" | "retrievalFailed" | "both" | null
    tavily_results: list[dict]


# ── Answer node system prompt ─────────────────────────────────────────────────
_ANSWER_SYSTEM = """You are a Malaysian tax guide for digital nomads and expats. You explain how Malaysian tax rules apply; you do not give formal tax advice or calculate final liabilities.

Tone:
- Use calm, professional language suitable for a regulated financial environment.
- No emoji, no checkmarks, no ALL CAPS, no dramatic formatting.
- Use conditional and neutral phrasing: "Based on what you've shared...", "If these conditions apply...", "This would typically depend on...", "To clarify how this may apply, it would help to know..."
- Never promise exact tax amounts, definitive obligations, or guaranteed outcomes.

Rules:
- Never give definitive tax advice; qualify with "generally", "typically", "based on the rules".
- Cite document names, section numbers, or thresholds when stating rules (e.g. "ITA s7(1)(a)", "PR 11/2017", "Schedule 6").
- Answer the user's question FIRST.
- If your context contains an [INSTRUCTION] block with a follow-up question, ask that question word for word at the end of your response — preceded by one short neutral bridge sentence such as "To understand how these rules may apply in your situation, it would help to know:". Do not output the [INSTRUCTION] block itself.
- Ask AT MOST ONE question per response. When an [INSTRUCTION] question is present, do NOT include any other question, call-to-action, or request for the user to provide profile data anywhere else in your response body.
- Keep responses concise and structured. No filler, padding, or repetition.

Faithfulness rule (critical):
- Base every factual claim strictly on text present in <retrieved_context>.
- Do not add thresholds, conditions, or rules from general knowledge if they are absent from the retrieved text.
- If a specific detail is not covered in the retrieved materials, say "the retrieved materials do not address [detail]" rather than inferring from memory.

Advice and calculation requests:
- If the user asks for exact tax payable, precise liability figures, confirmation they do or do not owe tax, or strategic planning advice:
  1. Explain the governing rule at a high level.
  2. Clarify what factors determine the outcome.
  3. State that final tax liability requires review by a licensed tax agent.
  4. Offer (once, neutrally): "If you'd like formal confirmation or filing support, a licensed tax agent can review your full facts."

Banned phrases (replace with softer language):
  "you should", "you definitely", "you don't need", "you are required to", "you must",
  "must provide", "I will give you exact", "definitively", "you will owe"
"""

# ── Controller node ───────────────────────────────────────────────────────────

def _build_profile_summary(profile: dict, decision_map: dict, today_iso: str | None = None) -> str:
    income = profile.get("incomeTypes") or {}
    active = [k for k, v in income.items() if v]
    trips = (profile.get("presence") or {}).get("trips") or []
    default_year = int(today_iso[:4]) if today_iso else 2025
    year = profile.get("assessmentYear") or default_year
    jurisdiction = profile.get("jurisdiction") or "MY"

    lines = [
        f"Profile: {jurisdiction} | Year {year}",
        f"Income: {', '.join(active) if active else 'none declared'}",
        f"Trips: {len(trips)} logged",
    ]

    if trips:
        for t in trips:
            entry = t.get("entryDate", "unknown")
            exit_ = t.get("exitDate", "unknown")
            lines.append(f"  Trip: {entry} → {exit_}")
        calc = presence_calculator(trips, year)
        lines.append(f"Days in jurisdiction ({year}): {calc['daysInYear']}")
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


def _build_flags(profile: dict, decision_map: dict, today_iso: str | None = None) -> list[dict]:
    flags = []
    trips = (profile.get("presence") or {}).get("trips") or []
    default_year = int(today_iso[:4]) if today_iso else 2025
    year = profile.get("assessmentYear") or default_year
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

    # Classify topic and freshness (deterministic; no LLM)
    freshness = detect_freshness(user_msg)
    topic = topic_classifier(user_msg)["topic"]

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
    flags = _build_flags(profile, dict(decision_map), today_iso)
    profile_summary = _build_profile_summary(profile, dict(decision_map), today_iso)

    # Compute suggested filing form
    trips = (profile.get("presence") or {}).get("trips") or []
    default_year = int(today_iso[:4]) if today_iso else 2025
    _year = profile.get("assessmentYear") or default_year
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

    # Log Tavily decision inputs (controller computes freshness + topic; actual trigger is post-retrieve)
    print(
        f"[CONTROLLER] intent={intent} "
        f"topic={topic} "
        f"freshnessRequested={freshness} "
        f"retrievalQuery={'yes' if retrieval_query else 'no'}"
    )

    return {
        "task_packet": task_packet,
        "profile": profile,
        "skipped_field_paths": skipped,
        "profile_patch": profile_patch,
        "retrieved_chunks": [],
        "freshness_requested": freshness,
        "topic": topic,
        "tavily_triggered": False,
        "tavily_reason": None,
        "tavily_results": [],
    }


# ── Retrieve node ─────────────────────────────────────────────────────────────

MIN_SCORE = 0.25  # Minimum Qdrant relevance score to consider retrieval successful

_HYDE_SYSTEM = (
    "You are a Malaysian tax law expert. Write a concise excerpt (3-5 sentences) from a "
    "Malaysian tax statute or LHDN public ruling that directly answers the question below. "
    "Use formal legal language and cite specific section numbers where possible. "
    "Do not add commentary, caveats, or advice — write only as the source document would."
)


async def _hyde_query(question: str) -> str:
    """HyDE: generate a hypothetical legal passage and use it as the embedding query.

    User queries are conversational; source chunks are formal legal text. Embedding a
    hypothetical answer written in the register of the source documents dramatically
    reduces the semantic gap and improves retrieval precision.
    Falls back to the original question if generation fails.
    """
    try:
        model = ModelProviderChatModel(timeout=20)
        response = await model.ainvoke([
            SystemMessage(content=_HYDE_SYSTEM),
            HumanMessage(content=question),
        ])
        text = response.content if isinstance(response.content, str) else question
        print(f"[HYDE] generated passage ({len(text)} chars) for query: {question[:60]}")
        return text
    except Exception as exc:
        print(f"[HYDE] fallback to original query: {exc}")
        return question


async def retrieve_node(state: AgentState) -> dict:
    task_packet = state.get("task_packet") or {}
    query = task_packet.get("retrievalQuery")
    if not query:
        return {"retrieved_chunks": [], "max_qdrant_score": 0.0}

    # HyDE: embed a hypothetical document instead of the raw user query
    embedding_query = await _hyde_query(query)

    vs = _get_vector_store()
    try:
        docs_and_scores = await asyncio.to_thread(
            vs.similarity_search_with_score, embedding_query, k=5
        )
    except Exception as exc:
        print(f"[RETRIEVE] Error: {exc}")
        return {"retrieved_chunks": [], "max_qdrant_score": 0.0}

    chunks = []
    scores = []
    for doc, score in docs_and_scores:
        meta = doc.metadata
        chunks.append({
            "chunkId": meta.get("chunk_id", str(uuid.uuid4())),
            "text": doc.page_content,
            "sectionRef": meta.get("reference", ""),
            "sourceTitle": meta.get("title", ""),
            "sourceUrl": meta.get("url", ""),
            "score": float(score),
        })
        scores.append(float(score))

    max_score = max(scores) if scores else 0.0

    # Log retrieval outcome
    print(
        f"[RETRIEVE] maxQdrantScore={max_score:.4f} "
        f"chunkCount={len(chunks)} "
        f"topic={state.get('topic', 'OTHER')} "
        f"freshnessRequested={state.get('freshness_requested', False)}"
    )

    return {"retrieved_chunks": chunks, "max_qdrant_score": max_score}


# ── Tavily lookup node ────────────────────────────────────────────────────────

from lib.tavily_tool import official_web_lookup, ALLOWED_TOPICS


async def tavily_lookup_node(state: AgentState) -> dict:
    """Call official_web_lookup and store results. Triggered only by controller routing."""
    messages = state["messages"]
    topic = state.get("topic", "OTHER")
    freshness = state.get("freshness_requested", False)
    max_score = state.get("max_qdrant_score", 0.0)

    # Determine reason
    retrieval_failed = max_score < MIN_SCORE
    if freshness and retrieval_failed:
        reason = "both"
    elif freshness:
        reason = "freshnessRequested"
    else:
        reason = "retrievalFailed"

    # Get the user's last message as the Tavily query
    last_human = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    raw_content = last_human.content if last_human else ""
    query = raw_content if isinstance(raw_content, str) else " ".join(
        p.get("text", "") if isinstance(p, dict) else str(p) for p in raw_content
    )

    tavily_results: list[dict] = []
    try:
        result = await asyncio.to_thread(official_web_lookup, query=query, topic=topic)
        tavily_results = result.get("results") or []
    except Exception as exc:
        print(f"[TAVILY] Error: {exc}")

    # Logging
    print(
        f"[TAVILY] tavily_triggered=True "
        f"tavily_reason={reason} "
        f"topic={topic} "
        f"maxQdrantScore={max_score:.4f} "
        f"tavilyResultCount={len(tavily_results)}"
    )

    return {
        "tavily_triggered": True,
        "tavily_reason": reason,
        "tavily_results": tavily_results,
    }


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

    tavily_results = state.get("tavily_results") or []
    if tavily_results:
        lines = ["⚡ Freshness note (from official LHDN pages — verify details directly):"]
        for r in tavily_results[:3]:  # top 3 findings
            title = r.get("title", "").strip()
            url = r.get("url", "").strip()
            snippet = r.get("snippet", "").strip()[:200]  # truncate long snippets
            date_str = r.get("publishedDate", "")
            line_parts = [f"- {title}"]
            if snippet:
                line_parts.append(f"  {snippet}")
            if url:
                line_parts.append(f"  Source: {url}")
            if date_str:
                line_parts.append(f"  Date: {date_str}")
            lines.append("\n".join(line_parts))
        context_parts.append(
            f"<freshness_addendum>\n"
            + "\n\n".join(lines)
            + "\n\nIMPORTANT: Use Tavily findings ONLY to flag potential updates. "
              "Do not invent new rules from snippets. If content is unclear, say: "
              "'I can't confirm the details from the snippet alone; please verify on the LHDN page or consult an agent.'"
            + "\n</freshness_addendum>"
        )

    suggested_form = task_packet.get("suggestedForm") or {}
    if suggested_form.get("decidable") and suggested_form.get("form"):
        context_parts.append(
            f"<suggested_form>{suggested_form['form']} — {suggested_form['reason']}</suggested_form>"
        )

    next_q = task_packet.get("nextQuestion")
    if next_q:
        context_parts.append(
            f"[INSTRUCTION — do not repeat this block in your response]\n"
            f"End your response with ONLY this question, word for word. "
            f"Do not ask any other question or include any call-to-action for profile data anywhere else in your response:\n"
            f"{next_q['question']}"
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
    "definitively": "generally",
    "you don't need": "you may not need",
    "you are required to": "it's generally required that",
    "you must": "it is generally required to",
    "must provide": "it would help to provide",
    "I will give you exact": "I can outline",
    "you will owe": "you may be liable for",
}

# Matches emoji characters across standard Unicode blocks
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001F9FF"   # symbols, pictographs, emoticons, transport
    "\U0000FE00-\U0000FE0F"    # variation selectors
    "\U00002600-\U000027BF"    # misc symbols (includes ✓ ✗ ☑ etc.)
    "\U0001FA00-\U0001FA9F"    # chess, medical, other symbols
    "\U00002702-\U000027B0"    # dingbats
    "]+",
    flags=re.UNICODE,
)

# Matches words written entirely in uppercase (3+ letters) outside markdown headings
_ALLCAPS_RE = re.compile(r"(?<![#*`])\b([A-Z]{3,})\b")


def _flatten_allcaps(match: re.Match) -> str:
    word = match.group(1)
    return word.title()


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

    # 1. Phrase softening
    for phrase, replacement in _SOFTENING.items():
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        new_text, count = pattern.subn(replacement, text)
        if count:
            text = new_text
            modified = True

    # 2. Remove emoji (multiple emoji signal dramatic tone; strip all for consistency)
    emoji_matches = _EMOJI_RE.findall(text)
    if len(emoji_matches) >= 2:
        text = _EMOJI_RE.sub("", text).strip()
        modified = True
        print(f"[CRITIC] Stripped {len(emoji_matches)} emoji")

    # 3. Flatten ALL CAPS words to title case (e.g. "IMPORTANT" → "Important")
    new_text, count = _ALLCAPS_RE.subn(_flatten_allcaps, text)
    if count:
        text = new_text
        modified = True
        print(f"[CRITIC] Flattened {count} ALL CAPS word(s)")

    # 4. Warn if >1 question mark (for monitoring)
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


def _should_tavily(state: AgentState) -> str:
    """After retrieval: decide whether to run Tavily fallback."""
    freshness = state.get("freshness_requested", False)
    max_score = state.get("max_qdrant_score", 0.0)
    topic = state.get("topic", "OTHER")
    retrieval_failed = max_score < MIN_SCORE

    if (freshness or retrieval_failed) and topic in ALLOWED_TOPICS:
        return "tavily_lookup"
    return "answer"


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
            builder.add_node("tavily_lookup", tavily_lookup_node)
            builder.add_node("answer", answer_node)
            builder.add_node("critic", critic_node)

            builder.set_entry_point("controller")
            builder.add_conditional_edges("controller", _should_retrieve,
                                          {"retrieve": "retrieve", "answer": "answer"})
            builder.add_conditional_edges("retrieve", _should_tavily,
                                          {"tavily_lookup": "tavily_lookup", "answer": "answer"})
            builder.add_edge("tavily_lookup", "answer")
            builder.add_edge("answer", "critic")
            builder.add_edge("critic", END)

            _graph = builder.compile(checkpointer=checkpointer)

    return _graph
