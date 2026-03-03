"""Configuration and factory for model providers. Reads API keys from env."""

import os
from dataclasses import dataclass
from typing import Any

from lib.model_provider.providers import AnthropicChatProvider, OpenAIProvider
from lib.model_provider.types import ChatMessage


@dataclass
class ModelProviderConfig:
    """Holds the active chat and embed providers plus their default models.

    Typed as Any so providers can be swapped (private model, OpenAI chat, etc.)
    without touching this dataclass. Both providers must satisfy:
      - chat_provider: async def chat(messages, *, model, ...) -> ChatResult | AsyncIterator[StreamChunk]
      - embed_provider: async def embed(texts, *, model) -> EmbedResult
    """

    chat_provider: Any
    embed_provider: Any
    default_chat_model: str
    default_embed_model: str


_default: ModelProviderConfig | None = None


def get_model_provider() -> ModelProviderConfig:
    """Singleton factory. Reads ANTHROPIC_API_KEY and OPENAI_API_KEY from env.
    Override defaults via MODEL_PROVIDER_CHAT_MODEL / MODEL_PROVIDER_EMBED_MODEL.
    """
    global _default
    if _default is None:
        chat_model = os.getenv("MODEL_PROVIDER_CHAT_MODEL", "claude-haiku-4-5-20251001")
        embed_model = os.getenv("MODEL_PROVIDER_EMBED_MODEL", "text-embedding-3-small")
        _default = ModelProviderConfig(
            chat_provider=AnthropicChatProvider(
                api_key=os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY"),
                default_model=chat_model,
            ),
            embed_provider=OpenAIProvider(
                api_key=os.getenv("OPENAI_API_KEY"),
                default_embed_model=embed_model,
            ),
            default_chat_model=chat_model,
            default_embed_model=embed_model,
        )
    return _default


async def chat(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    stream: bool = False,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: dict[str, Any] | str | None = None,
    response_format: dict[str, Any] | None = None,
    system: str | None = None,
) -> Any:
    """Async convenience wrapper: chat via the configured provider.
    Accepts messages as list of {"role": ..., "content": ...} dicts.
    """
    config = get_model_provider()
    msgs = [
        ChatMessage(role=m["role"], content=m["content"])
        for m in messages
        if isinstance(m, dict) and "role" in m and "content" in m
    ]
    return await config.chat_provider.chat(
        msgs,
        model=model or config.default_chat_model,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
        tools=tools,
        tool_choice=tool_choice,
        response_format=response_format,
        system=system,
    )


async def embed(texts: list[str], *, model: str | None = None) -> Any:
    """Async convenience wrapper: embed via the configured provider."""
    config = get_model_provider()
    return await config.embed_provider.embed(texts, model=model or config.default_embed_model)
