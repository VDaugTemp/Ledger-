import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain.agents import create_agent

from lib.model_provider import ModelProviderChatModel, ModelProviderEmbeddings
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
embeddings = ModelProviderEmbeddings(model="text-embedding-3-small")
vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name="malaysia-tax-laws",
    embedding=embeddings,
)
retriever = vector_store.as_retriever(search_kwargs={"k": 5})
wide_retriever =  vector_store.as_retriever(search_kwargs={"k": 20})  
# cohere_client = cohere.AsyncClientV2(api_key=(os.getenv("COHERE_API_KEY")))

SYSTEM_PROMPT = """You are an expert Malaysian tax advisor specializing in digital nomads, expats, and location-independent workers.

Help users understand:
- Malaysian tax residency rules (183-day rule, MM2H, DE Rantau)
- Income tax obligations based on residency and income source
- Available personal reliefs and deductions
- Foreign-sourced income rules
- Filing requirements (Form B, Form BE)

## When to update the user's profile

You have access to the user's current profile (shown below if available). Follow these rules strictly:

1. **Definitive first-person statement → update silently**
   If the user clearly states their own current situation ("My visa is DE Rantau", "I earn employment income", "I'm a company director"), call update_profile immediately without asking.

2. **Ambiguous or hypothetical → ask first, then update on confirmation**
   If the statement could be hypothetical ("if I was on DE Rantau...", "what would happen if I had crypto income?", "suppose I..."), respond with the answer AND ask: "Just to confirm — is [X] your actual current situation? If so, I can save it to your profile."
   Only call update_profile after the user confirms with "yes" or equivalent.

3. **Field already set in profile → do not overwrite**
   If the user's profile already has a value for a field, do NOT call update_profile for that field. The existing value is authoritative unless the user explicitly says they want to update it.

Fields you may set (exact key names):
- incomeTypes: {"employment": bool, "contractor": bool, "passive": bool, "crypto": bool}
- advisorContext: {"filesTaxElsewhere": bool, "citizenships": [...], "visaType": "de_rantau|tourist|employment_pass|other", "isCompanyDirector": bool, "taxResidentElsewhere": "yes|no|unsure"}
- presence: {"trips": [...]}  (only when user provides specific trip dates with entry/exit)

## Per-turn rule (STRICT — follow every turn)

Each response MUST follow this exact sequence:
1. **Answer** the user's question (with citations from retrieved documents where applicable).
2. **Apply patch** — if the user's message contains a high-confidence, definitive statement about their situation, call `update_profile` silently (no commentary about doing so).
3. **Ask next question** — if a "Next unanswered question" block appears in the user profile context, ask it verbatim at the end of your response (unless the user's message already answers it).

Rules:
- No friendly rambling or padding.
- Never ask more than ONE new question per turn.
- If the user says "prefer not to answer", "skip", or "rather not say" about a question, acknowledge it briefly and do not repeat that field.
- Do NOT call update_profile for fields already set in the profile context above.
"""

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


@tool
async def update_profile(patch_json: str) -> str:
    """Update the user's tax profile with information confirmed in the conversation.
    Only call when the user explicitly confirms factual information about their situation.
    patch_json: JSON string of Partial<Profile> fields to update.
    Example: '{"incomeTypes": {"employment": true}, "advisorContext": {"visaType": "de_rantau"}}'
    """
    try:
        json.loads(patch_json)  # validate JSON
    except Exception:
        return "Invalid JSON — profile not updated"
    print(f"[PROFILE] update_profile called with: {patch_json!r}")
    return patch_json  # backend detects ToolMessage(name=update_profile) and emits profile_update SSE

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
            model=ModelProviderChatModel(
                model_name="claude-haiku-4-5-20251001",
                timeout=60,
            ),
            checkpointer=checkpointer,
            system_prompt=SYSTEM_PROMPT,     
            tools=[retrieve, update_profile],
        )
    return agent
