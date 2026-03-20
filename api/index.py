# api/index.py
"""FastAPI server. Accepts Profile JSON from frontend; streams SSE back.

SSE events emitted:
  event: profile_update  — when controller extracted a profile patch
  event: message         — AI text chunks  [{"type": "AIMessageChunk", "content": "..."}, {}]
"""
from __future__ import annotations

import json
import os
import re
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import redis.asyncio as aioredis

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain_core.messages import AIMessage, HumanMessage

from lib.agent import get_graph, _get_qdrant_client
from lib.model_provider import get_model_provider
from lib.jailbreak_guard import is_jailbreak, warmup as jailbreak_warmup

load_dotenv()

_redis: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        if not url.startswith(("redis://", "rediss://", "unix://")):
            url = "redis://" + url
        _redis = aioredis.from_url(url, decode_responses=True)
    return _redis


_THREAD_TTL_SECONDS = 864_000  # 10 days

# Claude Haiku (claude-haiku-4-5-20251001) pricing
_HAIKU_INPUT_PRICE_PER_TOKEN = 0.80 / 1_000_000   # USD per input token
_HAIKU_OUTPUT_PRICE_PER_TOKEN = 4.00 / 1_000_000  # USD per output token
_USER_BUDGET_USD = 3.00


async def _get_user_cost(user_id: str) -> float:
    """Return total USD cost accumulated for this user."""
    r = await _get_redis()
    data = await r.hgetall(f"usage:{user_id}")
    input_tokens = int(data.get("input_tokens", 0))
    output_tokens = int(data.get("output_tokens", 0))
    return (input_tokens * _HAIKU_INPUT_PRICE_PER_TOKEN) + (output_tokens * _HAIKU_OUTPUT_PRICE_PER_TOKEN)


async def _add_user_tokens(user_id: str, input_tokens: int, output_tokens: int) -> None:
    """Atomically increment token counters for a user."""
    r = await _get_redis()
    key = f"usage:{user_id}"
    if input_tokens:
        await r.hincrby(key, "input_tokens", input_tokens)
    if output_tokens:
        await r.hincrby(key, "output_tokens", output_tokens)


async def _save_thread_metadata(user_id: str, thread_id: str, first_message: str) -> None:
    """Prepend thread metadata to threads:{user_id} Redis list. Sets TTL on first write."""
    r = await _get_redis()
    key = f"threads:{user_id}"
    entry = json.dumps(
        {
            "threadId": thread_id,
            "title": first_message[:60].strip(),
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
    )
    is_new = not await r.exists(key)
    # Prepend: LPUSH + trim to prevent unbounded growth (cap at 100 threads)
    await r.lpush(key, entry)
    await r.ltrim(key, 0, 99)
    if is_new:
        await r.expire(key, _THREAD_TTL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[STARTUP] Warming up singletons…")
    try:
        await get_graph()
        _get_qdrant_client()
        get_model_provider()
        jailbreak_warmup()
        print("[STARTUP] Warmup complete")
    except Exception as exc:
        print(f"[STARTUP] Warmup error (non-fatal): {exc}")
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


_SUMMARY_SYSTEM = """You are preparing a concise handoff note for a Malaysian tax accountant.

Write 2-4 sentences describing what this client was enquiring about in their AI-assisted conversation.

Cover: the main tax topics or questions raised (e.g. crypto treatment, DE Rantau implications, DTAs, FSI remittance), any notable concerns or flags, and the general nature of their situation.

Do NOT repeat profile fields (income type, visa, trip dates, etc.) — those are captured separately in the form.
Do NOT give tax advice or make definitive statements.
Write in third person: "This client is enquiring about..."
Be concise — 2-4 sentences maximum.
Output plain text only. No headers, labels, bold formatting, or prefixes (e.g. do not write "Handoff Note:" or "Summary:" before the text)."""


class ChatRequest(BaseModel):
    input: str
    config: dict[str, Any] | None = None
    # New fields: full Profile JSON from frontend
    profile: dict[str, Any] | None = None
    skipped_field_paths: list[str] | None = None
    today_iso: str | None = None
    # Legacy (backward compat — still accepted but not used if profile is present)
    profile_context: str | None = None
    user_id: str | None = None
    mode: str = "fast"  # "fast" | "private"


class SummaryRequest(BaseModel):
    thread_id: str


@app.get("/app/health")
async def health():
    return {"status": "ok"}


@app.get("/app/chat/threads")
async def list_threads(user_id: str):
    """Return thread metadata list for a user (most recent first)."""
    r = await _get_redis()
    key = f"threads:{user_id}"
    raw_entries = await r.lrange(key, 0, -1)
    threads = []
    for raw in raw_entries:
        try:
            threads.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return {"threads": threads}


@app.get("/app/chat/threads/{thread_id}/messages")
async def get_thread_messages(thread_id: str):
    """Return messages for a thread from LangGraph checkpoint state."""
    graph = await get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = await graph.aget_state(config)

    checkpoint_id = snapshot.config.get("configurable", {}).get("checkpoint_id")
    if checkpoint_id is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    messages = []
    for msg in snapshot.values.get("messages", []):
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content if isinstance(msg.content, str) else ""})
        elif isinstance(msg, AIMessage):
            messages.append({"role": "assistant", "content": msg.content if isinstance(msg.content, str) else ""})

    return {"messages": messages}


@app.post("/app/chat")
async def chat(payload: ChatRequest):
    # Quota check — only enforced for identified users
    if payload.user_id:
        current_cost = await _get_user_cost(payload.user_id)
        if current_cost >= _USER_BUDGET_USD:
            print(f"[QUOTA] Blocked user_id={payload.user_id!r} — cost ${current_cost:.4f} >= ${_USER_BUDGET_USD}")

            async def _quota_exceeded():
                yield (
                    f"event: error\n"
                    f"data: {json.dumps({'message': 'You have reached your usage limit for this service. Please contact support if you need further assistance.'})}\n\n"
                )

            return StreamingResponse(_quota_exceeded(), media_type="text/event-stream")

    if await is_jailbreak(payload.input):
        print(f"[JAILBREAK] Blocked input from user_id={payload.user_id!r}")

        async def _blocked():
            yield (
                f"event: error\n"
                f"data: {json.dumps({'message': 'Your message was flagged by our safety filter. Please rephrase your question.'})}\n\n"
            )

        return StreamingResponse(_blocked(), media_type="text/event-stream")

    graph = await get_graph()

    config = payload.config or {}
    configurable = config.get("configurable") or {}
    if "thread_id" not in configurable:
        configurable = {**configurable, "thread_id": str(uuid.uuid4())}
    config = {**config, "configurable": configurable}

    today_iso = payload.today_iso or datetime.now(timezone.utc).date().isoformat()
    profile = payload.profile or {}
    skipped = payload.skipped_field_paths or []

    initial_state = {
        "messages": [{"role": "user", "content": payload.input}],
        "profile": profile,
        "skipped_field_paths": skipped,
        "today_iso": today_iso,
        "task_packet": None,
        "retrieved_chunks": [],
        "profile_patch": None,
        # Tavily-related
        "freshness_requested": False,
        "topic": "OTHER",
        "max_qdrant_score": 0.0,
        "tavily_triggered": False,
        "tavily_reason": None,
        "tavily_results": [],
        "mode": payload.mode,
    }

    # Auto-save thread metadata on first turn
    thread_id = configurable.get("thread_id", "")
    if payload.user_id and thread_id:
        snapshot = await graph.aget_state(config)
        is_new_thread = snapshot.config.get("configurable", {}).get("checkpoint_id") is None
        if is_new_thread:
            await _save_thread_metadata(payload.user_id, thread_id, payload.input)

    async def stream():
        text_started = False
        _session_input_tokens = 0
        _session_output_tokens = 0
        try:
            async for event in graph.astream_events(initial_state, config=config, version="v2"):
                etype = event.get("event", "")
                ename = event.get("name", "")

                # Capture token usage from LLM responses
                if etype == "on_chat_model_end":
                    output = event.get("data", {}).get("output")
                    if output is not None:
                        usage = getattr(output, "usage_metadata", None) or {}
                        _session_input_tokens += int(usage.get("input_tokens", 0))
                        _session_output_tokens += int(usage.get("output_tokens", 0))

                # Profile patch: emit immediately after controller completes
                if etype == "on_chain_end" and ename == "controller":
                    output = event.get("data", {}).get("output") or {}
                    patch = output.get("profile_patch")
                    if patch:
                        yield (
                            f"event: profile_update\n"
                            f"data: {json.dumps(patch, default=str)}\n\n"
                        )
                    yield f"event: status\ndata: {json.dumps({'status': 'retrieving'})}\n\n"

                # Signal that retrieval is complete and answering is starting
                elif etype == "on_chain_end" and ename == "retrieve":
                    yield f"event: status\ndata: {json.dumps({'status': 'answering'})}\n\n"

                # Token streaming from LLM (fires during answer node)
                elif etype == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk:
                        content = chunk.content if hasattr(chunk, "content") else ""
                        if isinstance(content, str) and content:
                            msg_data = [{"type": "AIMessageChunk", "content": content}, {}]
                            yield f"event: message\ndata: {json.dumps(msg_data)}\n\n"
                            text_started = True

                # Fallback: full response on answer node completion (if streaming didn't fire)
                elif etype == "on_chain_end" and ename == "answer" and not text_started:
                    output = event.get("data", {}).get("output") or {}
                    msgs = output.get("messages") or []
                    for msg in msgs:
                        content = msg.content if hasattr(msg, "content") else ""
                        if isinstance(content, str) and content:
                            msg_data = [{"type": "AIMessageChunk", "content": content}, {}]
                            yield f"event: message\ndata: {json.dumps(msg_data)}\n\n"

        except Exception as exc:
            # Log the full error for server-side diagnostics.
            print(f"[STREAM] Error: {exc}")
            traceback.print_exc()
            # Yield a structured error event so the frontend can display a message
            # rather than seeing an abrupt connection close / ASGI crash.
            yield (
                f"event: error\n"
                f"data: {json.dumps({'message': str(exc)}, default=str)}\n\n"
            )
        finally:
            # Persist token usage for this turn regardless of success/failure
            if payload.user_id and (_session_input_tokens or _session_output_tokens):
                await _add_user_tokens(payload.user_id, _session_input_tokens, _session_output_tokens)
                turn_cost = (
                    _session_input_tokens * _HAIKU_INPUT_PRICE_PER_TOKEN
                    + _session_output_tokens * _HAIKU_OUTPUT_PRICE_PER_TOKEN
                )
                print(
                    f"[QUOTA] user_id={payload.user_id!r} "
                    f"turn={_session_input_tokens}in/{_session_output_tokens}out "
                    f"(${turn_cost:.5f})"
                )

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/app/chat/eval")
async def chat_eval(
    payload: ChatRequest,
    x_eval_mode: str = Header(default="0"),
):
    """Eval-mode endpoint: returns structured JSON (answer + contexts + policy).
    Activate with header X-Eval-Mode: 1.
    Only for evaluation — not used by the frontend.
    """
    if x_eval_mode != "1":
        return {"error": "Set X-Eval-Mode: 1 header to use eval mode"}

    graph = await get_graph()

    config = payload.config or {}
    configurable = config.get("configurable") or {}
    if "thread_id" not in configurable:
        configurable = {**configurable, "thread_id": str(uuid.uuid4())}
    config = {**config, "configurable": configurable}

    today_iso = payload.today_iso or datetime.now(timezone.utc).date().isoformat()
    profile = payload.profile or {}
    skipped = payload.skipped_field_paths or []

    initial_state = {
        "messages": [{"role": "user", "content": payload.input}],
        "profile": profile,
        "skipped_field_paths": skipped,
        "today_iso": today_iso,
        "task_packet": None,
        "retrieved_chunks": [],
        "profile_patch": None,
        "freshness_requested": False,
        "topic": "OTHER",
        "max_qdrant_score": 0.0,
        "tavily_triggered": False,
        "tavily_reason": None,
        "tavily_results": [],
        "mode": payload.mode,
    }

    try:
        final_state = await graph.ainvoke(initial_state, config=config)
    except Exception as exc:
        return {"error": str(exc)}

    # Extract final AI answer
    from langchain_core.messages import AIMessage
    messages = final_state.get("messages") or []
    last_ai = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
    answer_text = ""
    if last_ai:
        answer_text = last_ai.content if isinstance(last_ai.content, str) else ""

    # Build contexts list
    raw_chunks = final_state.get("retrieved_chunks") or []
    contexts = [
        {
            "chunk_id": c.get("chunkId", ""),
            "text": c.get("text", ""),
            "section_ref": c.get("sectionRef", ""),
            "score": c.get("score", 0.0),
        }
        for c in raw_chunks
    ]

    # Build policy block
    task_packet = final_state.get("task_packet") or {}
    next_q = task_packet.get("nextQuestion")
    next_q_field = next_q["fieldPath"] if next_q else None

    q_count = answer_text.count("?")
    citations_present = bool(
        re.search(r"\b(s\d+|Section\s+\d+|PR\s+\d+|Article\s+\d+|Schedule\s+\d+|Form\s+[BEM]E?)\b", answer_text)
    )
    advice_leak = bool(
        re.search(r"\b(you should|you must|definitely|you don't need|I recommend)\b", answer_text, re.IGNORECASE)
    )

    policy = {
        "intent": task_packet.get("intent", "INFO"),
        "next_question_field": next_q_field,
        "num_questions": q_count,
        "citations_present": citations_present,
        "advice_leak": advice_leak,
    }

    return {
        "answer": answer_text,
        "contexts": contexts,
        "policy": policy,
    }


@app.post("/app/chat/summary")
async def chat_summary(payload: SummaryRequest):
    from langchain_core.messages import HumanMessage as LCHuman, AIMessage as LCAi, SystemMessage

    graph = await get_graph()
    config = {"configurable": {"thread_id": payload.thread_id}}

    try:
        snapshot = await graph.aget_state(config)
    except Exception as exc:
        return {"error": f"Could not retrieve conversation: {exc}"}

    messages = (snapshot.values or {}).get("messages") or []

    # Build compact transcript from last 20 messages
    lines: list[str] = []
    for msg in messages[-20:]:
        if isinstance(msg, LCHuman):
            content = msg.content if isinstance(msg.content, str) else ""
            if content:
                lines.append(f"Client: {content}")
        elif isinstance(msg, LCAi):
            content = msg.content if isinstance(msg.content, str) else ""
            if content:
                lines.append(f"Advisor: {content[:400]}")  # truncate long turns

    if not lines:
        return {"summary": ""}

    transcript = "\n".join(lines)

    try:
        from lib.model_provider import ModelProviderChatModel
        model = ModelProviderChatModel(timeout=20)
        response = await model.ainvoke([
            SystemMessage(content=_SUMMARY_SYSTEM),
            LCHuman(content=f"Conversation transcript:\n\n{transcript}"),
        ])
        summary = response.content if isinstance(response.content, str) else ""
        return {"summary": summary}
    except Exception as exc:
        return {"error": str(exc)}
