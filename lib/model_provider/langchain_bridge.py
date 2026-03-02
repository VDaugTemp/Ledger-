"""LangChain integration: Embeddings and ChatModel that delegate to ModelProvider."""

import asyncio
import concurrent.futures
from collections.abc import AsyncIterator, Iterator
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from lib.model_provider.config import get_model_provider
from lib.model_provider.types import ChatMessage


def _lc_messages_to_provider(messages: list[BaseMessage]) -> tuple[str | None, list[ChatMessage]]:
    """Convert LangChain messages to our ChatMessage format.
    SystemMessage content is extracted and returned as a separate system string.
    """
    system: str | None = None
    out: list[ChatMessage] = []
    for m in messages:
        if isinstance(m, SystemMessage):
            system = m.content if isinstance(m.content, str) else str(m.content)
            continue
        role = "user" if isinstance(m, HumanMessage) else "assistant"
        # Cast to Any: LangChain content can be list[str | dict] (multimodal),
        # which is a superset of ChatMessage's list[dict[str, Any]]. Safe at runtime.
        content: Any = m.content if isinstance(m.content, (str, list)) else str(m.content)
        out.append(ChatMessage(role=role, content=content))
    return system, out


def _run_async(coro: Any) -> Any:
    """Run an async coroutine from a sync context, handling already-running loops."""
    try:
        asyncio.get_running_loop()
        # Already inside an async context — run in a separate thread
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        return asyncio.run(coro)


class ModelProviderEmbeddings(Embeddings):
    """LangChain Embeddings backed by ModelProvider. No direct OpenAI SDK usage here."""

    def __init__(self, *, model: str | None = None):
        self._model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return _run_async(self.aembed_documents(texts))

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        config = get_model_provider()
        result = await config.embed_provider.embed(texts, model=self._model or config.default_embed_model)
        return result.embeddings

    async def aembed_query(self, text: str) -> list[float]:
        results = await self.aembed_documents([text])
        return results[0]


class ModelProviderChatModel(BaseChatModel):
    """LangChain ChatModel backed by ModelProvider (Anthropic). Supports async streaming."""

    model_name: str = "claude-3-5-haiku-20241022"
    temperature: float = 0.0
    max_tokens: int = 4096
    timeout: int | None = 60

    @property
    def _llm_type(self) -> str:
        return "model_provider_anthropic"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        return _run_async(self._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs))

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        system, provider_messages = _lc_messages_to_provider(messages)
        config = get_model_provider()
        result = await config.chat_provider.chat(
            provider_messages,
            model=kwargs.get("model") or self.model_name,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            stream=False,
            tools=kwargs.get("tools"),
            tool_choice=kwargs.get("tool_choice"),
            response_format=kwargs.get("response_format"),
            system=system,
        )
        msg = AIMessage(content=result.content)
        msg.response_metadata = {
            "usage": {
                "prompt_tokens": result.usage.prompt_tokens,
                "completion_tokens": result.usage.completion_tokens,
                "total_tokens": result.usage.total_tokens,
                "latency_ms": result.usage.latency_ms,
                "provider": result.usage.provider,
                "model": result.usage.model,
            }
        }
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Sync streaming bridge. In practice the agent uses _astream directly."""
        chunks: list[ChatGenerationChunk] = []

        async def _collect() -> list[ChatGenerationChunk]:
            return [c async for c in self._astream(messages, stop=stop, run_manager=run_manager, **kwargs)]

        chunks = _run_async(_collect())
        yield from chunks

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        system, provider_messages = _lc_messages_to_provider(messages)
        config = get_model_provider()
        stream_iter = await config.chat_provider.chat(
            provider_messages,
            model=kwargs.get("model") or self.model_name,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            stream=True,
            tools=kwargs.get("tools"),
            tool_choice=kwargs.get("tool_choice"),
            response_format=kwargs.get("response_format"),
            system=system,
        )
        async for chunk in stream_iter:
            if chunk.content_delta:
                yield ChatGenerationChunk(message=AIMessageChunk(content=chunk.content_delta))
            if chunk.usage is not None:
                # response_metadata goes on AIMessageChunk, not ChatGenerationChunk
                yield ChatGenerationChunk(
                    message=AIMessageChunk(
                        content="",
                        response_metadata={
                            "usage": {
                                "prompt_tokens": chunk.usage.prompt_tokens,
                                "completion_tokens": chunk.usage.completion_tokens,
                                "total_tokens": chunk.usage.total_tokens,
                                "latency_ms": chunk.usage.latency_ms,
                                "provider": chunk.usage.provider,
                                "model": chunk.usage.model,
                            }
                        },
                    )
                )
