"""Configuration and factory for model providers. Reads API keys from env."""

import os
from dataclasses import dataclass
from typing import Any

from lib.model_provider.providers import AnthropicChatProvider, FireworksChatProvider, OpenAIProvider
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
    default_temperature: float = 0.0
    default_max_tokens: int = 4096


_default: ModelProviderConfig | None = None
_fireworks: ModelProviderConfig | None = None


def _parse_float(val: str | None, fallback: float) -> float:
    try:
        return float(val) if val is not None else fallback
    except ValueError:
        return fallback


def _parse_int(val: str | None, fallback: int) -> int:
    try:
        return int(val) if val is not None else fallback
    except ValueError:
        return fallback


def get_model_provider() -> ModelProviderConfig:
    """Singleton factory for the Anthropic (fast) provider.

    Env vars read:
      ANTHROPIC_API_KEY / CLAUDE_API_KEY   — API key
      MODEL_PROVIDER_CHAT_MODEL            — override chat model (default: claude-haiku-4-5-20251001)
      MODEL_PROVIDER_EMBED_MODEL           — override embed model (default: text-embedding-3-small)
      ANTHROPIC_TEMPERATURE                — temperature (overrides LLM_DEFAULT_TEMPERATURE)
      ANTHROPIC_MAX_TOKENS                 — max tokens (overrides LLM_DEFAULT_MAX_TOKENS)
      LLM_DEFAULT_TEMPERATURE              — fallback temperature for all providers
      LLM_DEFAULT_MAX_TOKENS               — fallback max tokens for all providers
    """
    global _default
    if _default is None:
        chat_model = os.getenv("MODEL_PROVIDER_CHAT_MODEL", "claude-haiku-4-5-20251001")
        embed_model = os.getenv("MODEL_PROVIDER_EMBED_MODEL", "text-embedding-3-small")
        global_temp = _parse_float(os.getenv("LLM_DEFAULT_TEMPERATURE"), 0.0)
        global_max_tokens = _parse_int(os.getenv("LLM_DEFAULT_MAX_TOKENS"), 4096)
        temperature = _parse_float(os.getenv("ANTHROPIC_TEMPERATURE"), global_temp)
        max_tokens = _parse_int(os.getenv("ANTHROPIC_MAX_TOKENS"), global_max_tokens)
        _default = ModelProviderConfig(
            chat_provider=AnthropicChatProvider(
                api_key=os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY"),
                default_model=chat_model,
                default_temperature=temperature,
                default_max_tokens=max_tokens,
            ),
            embed_provider=OpenAIProvider(
                api_key=os.getenv("OPENAI_API_KEY"),
                default_embed_model=embed_model,
            ),
            default_chat_model=chat_model,
            default_embed_model=embed_model,
            default_temperature=temperature,
            default_max_tokens=max_tokens,
        )
    return _default


def get_model_provider_for_mode(mode: str = "fast") -> ModelProviderConfig:
    """Return provider config for the given mode.

    mode="fast"    → AnthropicChatProvider (default singleton)
    mode="private" → FireworksChatProvider

    Fireworks env vars read:
      FIREWORKS_API_KEY        — API key
      FIREWORKS_MODEL          — model ID (default: accounts/fireworks/models/qwen2p5-vl-32b-instruct)
      FIREWORKS_BASE_URL       — base URL (trailing /chat/completions is stripped automatically)
      FIREWORKS_TEMPERATURE    — temperature (overrides LLM_DEFAULT_TEMPERATURE)
      FIREWORKS_MAX_TOKENS     — max tokens (overrides LLM_DEFAULT_MAX_TOKENS)
      LLM_DEFAULT_TEMPERATURE  — fallback temperature for all providers
      LLM_DEFAULT_MAX_TOKENS   — fallback max tokens for all providers
    """
    if mode == "private":
        global _fireworks
        if _fireworks is None:
            fireworks_model = os.getenv(
                "FIREWORKS_MODEL",
                "accounts/fireworks/models/qwen2p5-vl-32b-instruct",
            )
            fireworks_base_url = os.getenv(
                "FIREWORKS_BASE_URL",
                "https://api.fireworks.ai/inference/v1",
            )
            embed_model = os.getenv("MODEL_PROVIDER_EMBED_MODEL", "text-embedding-3-small")
            global_temp = _parse_float(os.getenv("LLM_DEFAULT_TEMPERATURE"), 0.0)
            global_max_tokens = _parse_int(os.getenv("LLM_DEFAULT_MAX_TOKENS"), 4096)
            temperature = _parse_float(os.getenv("FIREWORKS_TEMPERATURE"), global_temp)
            max_tokens = _parse_int(os.getenv("FIREWORKS_MAX_TOKENS"), global_max_tokens)
            _fireworks = ModelProviderConfig(
                chat_provider=FireworksChatProvider(
                    api_key=os.getenv("FIREWORKS_API_KEY"),
                    default_model=fireworks_model,
                    base_url=fireworks_base_url,
                    default_temperature=temperature,
                    default_max_tokens=max_tokens,
                ),
                embed_provider=OpenAIProvider(
                    api_key=os.getenv("OPENAI_API_KEY"),
                    default_embed_model=embed_model,
                ),
                default_chat_model=fireworks_model,
                default_embed_model=embed_model,
                default_temperature=temperature,
                default_max_tokens=max_tokens,
            )
        return _fireworks
    return get_model_provider()


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
