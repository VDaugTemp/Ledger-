"""Provider implementations. Vendor SDKs (anthropic, openai) are imported only here."""

import time
from collections.abc import AsyncIterator
from typing import Any

from lib.model_provider.exceptions import (
    AuthError,
    InvalidRequestError,
    ModelProviderError,
    ProviderError,
    RateLimitError,
)
from lib.model_provider.types import (
    ChatMessage,
    ChatResult,
    EmbedResult,
    StreamChunk,
    Usage,
)


def _normalize_error(
    e: Exception,
    *,
    status_code: int | None,
    body: str | None,
) -> ModelProviderError:
    """Classify a vendor exception into our normalized error hierarchy.
    Secrets are stripped from body before storing in vendor_payload.
    """
    msg = str(e)
    payload: dict[str, Any] = {"type": type(e).__name__, "message": msg, "status_code": status_code}
    if body:
        payload["body"] = "[REDACTED]" if "api_key" in body.lower() else body

    if status_code == 429 or "rate" in msg.lower():
        return RateLimitError(msg, vendor_payload=payload)
    if status_code in (401, 403) or "auth" in msg.lower():
        return AuthError(msg, vendor_payload=payload)
    if status_code in (400, 404) or "invalid" in msg.lower():
        return InvalidRequestError(msg, vendor_payload=payload)
    return ProviderError(msg, vendor_payload=payload)


def _normalize_anthropic_error(e: Exception) -> ModelProviderError:
    resp = getattr(e, "response", None)
    return _normalize_error(
        e,
        status_code=getattr(resp, "status_code", None),
        body=getattr(resp, "text", None),
    )


def _normalize_openai_error(e: Exception) -> ModelProviderError:
    status_code = getattr(e, "status_code", None)
    if status_code is None:
        status_code = getattr(getattr(e, "response", None), "status_code", None)
    body = getattr(getattr(e, "response", None), "text", None)
    return _normalize_error(e, status_code=status_code, body=body)


def _messages_to_anthropic(
    messages: list[ChatMessage], system: str | None
) -> tuple[str | None, list[dict[str, Any]]]:
    """Convert our messages to Anthropic format. System role goes to the system param."""
    out: list[dict[str, Any]] = []
    system_out = system
    for m in messages:
        if m.role == "system":
            system_out = m.content if isinstance(m.content, str) else str(m.content)
            continue
        if m.role not in ("user", "assistant"):
            continue
        out.append({"role": m.role, "content": m.content})
    return system_out, out


class AnthropicChatProvider:
    """Anthropic chat. Vendor SDK imported lazily so it's only needed at call time."""

    def __init__(self, api_key: str | None = None, default_model: str = "claude-3-5-haiku-20241022"):
        self._api_key = api_key
        self._default_model = default_model
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            import anthropic
            # api_key=None means AsyncAnthropic reads ANTHROPIC_API_KEY from env automatically
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        stream: bool = False,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | str | None = None,
        response_format: dict[str, Any] | None = None,
        system: str | None = None,
    ) -> "ChatResult | AsyncIterator[StreamChunk]":
        model = model or self._default_model
        system_param, anthropic_messages = _messages_to_anthropic(messages, system)
        client = self._get_client()

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": anthropic_messages,
            "temperature": temperature,
        }
        if system_param:
            kwargs["system"] = system_param
        if tools:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        if response_format is not None:
            kwargs["output_format"] = response_format

        start = time.perf_counter()
        try:
            if stream:
                return self._stream_chat(client, kwargs, model, start)
            response = await client.messages.create(**kwargs)
            latency_ms = (time.perf_counter() - start) * 1000
            u = Usage(
                provider="anthropic",
                model=model,
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                latency_ms=latency_ms,
                request_id=getattr(response, "id", None),
            )
            text = "".join(block.text for block in response.content if hasattr(block, "text"))
            return ChatResult(content=text, usage=u, finish_reason="end_turn")
        except Exception as e:
            if isinstance(e, ModelProviderError):
                raise
            raise _normalize_anthropic_error(e)

    async def _stream_chat(
        self,
        client: Any,
        kwargs: dict[str, Any],
        model: str,
        start: float,
    ) -> AsyncIterator[StreamChunk]:
        usage_so_far: Usage | None = None
        try:
            # Note: .stream() is the SDK's streaming context manager — do NOT pass stream=True
            async with client.messages.stream(**kwargs) as stream:
                async for event in stream:
                    if not hasattr(event, "type"):
                        continue
                    if event.type == "content_block_delta":
                        text = getattr(getattr(event, "delta", None), "text", None)
                        if text:
                            yield StreamChunk(content_delta=text)
                    elif event.type == "message_delta":
                        delta = getattr(event, "delta", None)
                        raw_usage = getattr(delta, "usage", None) if delta else None
                        if raw_usage:
                            usage_so_far = Usage(
                                provider="anthropic",
                                model=model,
                                prompt_tokens=getattr(raw_usage, "input_tokens", 0) or 0,
                                completion_tokens=getattr(raw_usage, "output_tokens", 0) or 0,
                                total_tokens=0,
                                latency_ms=(time.perf_counter() - start) * 1000,
                            )
                    elif event.type == "message_stop":
                        yield StreamChunk(content_delta="", usage=usage_so_far, finish_reason="end_turn")
                        break
        except Exception as e:
            if isinstance(e, ModelProviderError):
                raise
            raise _normalize_anthropic_error(e)


class OpenAIProvider:
    """OpenAI embeddings. Vendor SDK imported lazily."""

    def __init__(self, api_key: str | None = None, default_embed_model: str = "text-embedding-3-small"):
        self._api_key = api_key
        self._default_embed_model = default_embed_model
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import AsyncOpenAI
            # api_key=None means AsyncOpenAI reads OPENAI_API_KEY from env automatically
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> EmbedResult:
        model = model or self._default_embed_model
        client = self._get_client()
        start = time.perf_counter()
        try:
            response = await client.embeddings.create(input=texts, model=model)
            latency_ms = (time.perf_counter() - start) * 1000
            u = Usage(
                provider="openai",
                model=model,
                prompt_tokens=getattr(response.usage, "prompt_tokens", 0) or 0,
                completion_tokens=0,
                total_tokens=getattr(response.usage, "total_tokens", 0) or 0,
                latency_ms=latency_ms,
                request_id=getattr(response, "id", None),
            )
            return EmbedResult(embeddings=[item.embedding for item in response.data], usage=u)
        except Exception as e:
            if isinstance(e, ModelProviderError):
                raise
            raise _normalize_openai_error(e)
