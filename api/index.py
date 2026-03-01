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

    async def stream():
        async for message, metadata in agent.astream(
            {"messages": [{"role": "user", "content": payload.input}]},
            config=config,
            stream_mode="messages",
        ):
            yield (
                f"event: message\n"
                f"data: {json.dumps([message.model_dump(mode='json'), metadata], default=str)}\n\n"
            )

    return StreamingResponse(stream(), media_type="text/event-stream")