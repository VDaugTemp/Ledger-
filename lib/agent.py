import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langchain_openai import OpenAIEmbeddings
from langchain.agents import create_agent
from langchain_qdrant import QdrantVectorStore
from langgraph.checkpoint.redis import AsyncRedisSaver
from qdrant_client import QdrantClient

ROOT_DIR = Path(__file__).resolve().parents[1]

load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / ".env.local", override=True)

checkpointer: AsyncRedisSaver | None = None  
agent: Any | None = None

qdrant_client: QdrantClient | None = QdrantClient(
    url=os.getenv("QDRANT_URL"), 
    api_key=os.getenv("QDRANT_API_KEY")
)
qdrant_collection = qdrant_client.get_collection("malaysia-tax-laws")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name="malaysia-tax-laws",
    embedding=embeddings,
)
retriever = vector_store.as_retriever(search_kwargs={"k": 6})

SYSTEM_PROMPT = "You are a helpful assistant that can answer questions and help with tasks."

@tool
async def retrieve(query: str) -> str:
    """Retrieve documents from the vector store."""
    print(f"[RAG] retrieve called with query: {query!r}")
    docs = await retriever.ainvoke(query)
    results = []
    for doc in docs:
        meta = doc.metadata
        source = f"[{meta.get('title', 'Unknown')} — {meta.get('reference', '')}]"
        results.append(f"{source}\n{doc.page_content}")
    print(f"[RAG] retrieved {len(results)} documents")
    return "\n\n---\n\n".join(results)

async def get_agent():
    global agent
    if agent is None:
        redis_url = os.getenv("REDIS_URL") or ""
        if not redis_url.strip():
            raise ValueError("REDIS_URL is not set. Set REDIS_URL in .env (e.g. redis://host:port)")
        redis_url = redis_url.strip()
        if not redis_url.startswith(("redis://", "rediss://", "unix://")):
            redis_url = "redis://" + redis_url
        checkpointer = AsyncRedisSaver(
            redis_url=redis_url,
            checkpoint_prefix="tax-agent-checkpointer",
        )
        await checkpointer.asetup()
        agent = create_agent(
            model=ChatAnthropic(
                model_name="claude-haiku-4-5",
                timeout=60,
                stop=None,
            ),
            checkpointer=checkpointer,
            system_prompt=SYSTEM_PROMPT,     
            tools=[retrieve],
        )
    return agent
