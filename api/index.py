from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Any
from lib.agent import get_agent
import json
import uuid


load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

class ChatRequest(BaseModel):
    input: str
    config: dict[str, Any] | None = None
    profile_context: str | None = None
    user_id: str | None = None

@app.get("/app/health")
async def health():
    return {"status": "ok"}

@app.post("/app/chat")
async def chat(payload: ChatRequest):
    agent = await get_agent()
    config = payload.config or {}
    configurable = config.get("configurable") or {}
    if "thread_id" not in configurable:
        configurable = {**configurable, "thread_id": str(uuid.uuid4())}
    config = {**config, "configurable": configurable}

    # Prepend profile context to user's input so agent has current user state
    effective_input = payload.input
    if payload.profile_context:
        effective_input = f"<user_profile>\n{payload.profile_context}\n</user_profile>\n\n{payload.input}"

    async def stream():
        async for message, metadata in agent.astream(
            {"messages": [{"role": "user", "content": effective_input}]},
            config=config,
            stream_mode="messages",
        ):
            msg_data = message.model_dump(mode='json')
            # Intercept update_profile tool results and emit as a separate SSE event
            if msg_data.get('type') == 'tool' and msg_data.get('name') == 'update_profile':
                yield (
                    f"event: profile_update\n"
                    f"data: {msg_data.get('content', '{}')}\n\n"
                )
            # Always emit the regular message event
            yield (
                f"event: message\n"
                f"data: {json.dumps([msg_data, metadata], default=str)}\n\n"
            )

    return StreamingResponse(stream(), media_type="text/event-stream")