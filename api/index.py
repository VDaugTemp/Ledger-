# api/index.py
"""FastAPI server. Accepts Profile JSON from frontend; streams SSE back.

SSE events emitted:
  event: profile_update  — when controller extracted a profile patch
  event: message         — AI text chunks  [{"type": "AIMessageChunk", "content": "..."}, {}]
"""
from __future__ import annotations

import json
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from lib.agent import get_graph

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/app/health")
async def health():
    return {"status": "ok"}


@app.post("/app/chat")
async def chat(payload: ChatRequest):
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
    }

    async def stream():
        text_started = False
        try:
            async for event in graph.astream_events(initial_state, config=config, version="v2"):
                etype = event.get("event", "")
                ename = event.get("name", "")

                # Profile patch: emit immediately after controller completes
                if etype == "on_chain_end" and ename == "controller":
                    output = event.get("data", {}).get("output") or {}
                    patch = output.get("profile_patch")
                    if patch:
                        yield (
                            f"event: profile_update\n"
                            f"data: {json.dumps(patch, default=str)}\n\n"
                        )

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

    return StreamingResponse(stream(), media_type="text/event-stream")
