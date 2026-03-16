"""Provider implementations. Vendor SDKs (anthropic, openai) are imported only here."""

import asyncio
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
    status_code = getattr(resp, "status_code", None)
    try:
        body = resp.text if resp is not None else None
    except Exception:
        body = None
    return _normalize_error(e, status_code=status_code, body=body)


def _normalize_openai_error(e: Exception) -> ModelProviderError:
    status_code = getattr(e, "status_code", None)
    resp = getattr(e, "response", None)
    if status_code is None:
        status_code = getattr(resp, "status_code", None)
    try:
        body = resp.text if resp is not None else None
    except Exception:
        body = None
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


_OVERLOAD_FALLBACK_MODEL = "claude-3-5-haiku-20241022"
# Delays (seconds) for application-level overload retries, applied AFTER the SDK's
# own max_retries=2 exponential backoff (which caps at 8 s per attempt).
_OVERLOAD_RETRY_DELAYS = (15.0, 30.0)


def _is_overload_error(e: Exception) -> bool:
    msg = str(e).lower()
    return "529" in str(e) or "overloaded_error" in msg or "overloaded" in msg


class AnthropicChatProvider:
    """Anthropic chat. Vendor SDK imported lazily so it's only needed at call time."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "claude-3-5-haiku-20241022",
        default_temperature: float = 0.0,
        default_max_tokens: int = 4096,
    ):
        self._api_key = api_key
        self._default_model = default_model
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def _single_chat(
        self,
        client: Any,
        kwargs: dict[str, Any],
        model: str,
        start: float,
        stream: bool,
    ) -> "ChatResult | AsyncIterator[StreamChunk]":
        """One attempt at the Anthropic API (no application-level retry)."""
        if stream:
            return self._stream_chat(client, {**kwargs, "model": model}, model, start)
        response = await client.messages.create(**{**kwargs, "model": model})
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
        tool_calls = [
            {"id": block.id, "name": block.name, "input": dict(block.input) if block.input else {}}
            for block in response.content
            if getattr(block, "type", None) == "tool_use"
        ]
        return ChatResult(content=text, usage=u, finish_reason="end_turn", tool_calls=tool_calls)

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
        target_model = model or self._default_model
        system_param, anthropic_messages = _messages_to_anthropic(messages, system)
        client = self._get_client()

        kwargs: dict[str, Any] = {
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

        # Application-level overload retry: SDK caps its own backoff at 8 s; persistent
        # 529 errors need longer waits and/or a fallback to a more available model.
        # Schedule: primary model → wait 15 s → primary again → wait 30 s → fallback model.
        attempts: list[tuple[str, float | None]] = [
            (target_model, _OVERLOAD_RETRY_DELAYS[0]),
            (target_model, _OVERLOAD_RETRY_DELAYS[1]),
            (_OVERLOAD_FALLBACK_MODEL, None),
        ]
        # Collapse duplicate model entries when already on the fallback model.
        if target_model == _OVERLOAD_FALLBACK_MODEL:
            attempts = [(target_model, d) for _, d in attempts]

        last_error: Exception | None = None
        for attempt_model, delay_before_next in attempts:
            start = time.perf_counter()
            try:
                return await self._single_chat(client, kwargs, attempt_model, start, stream)
            except Exception as e:
                if isinstance(e, ModelProviderError):
                    if not _is_overload_error(e):
                        raise
                    last_error = e
                else:
                    normalized = _normalize_anthropic_error(e)
                    if not _is_overload_error(normalized):
                        raise normalized
                    last_error = normalized

                used = "fallback" if attempt_model != target_model else attempt_model
                print(
                    f"[ANTHROPIC] Overload on {used!r}; "
                    + (f"retrying in {delay_before_next}s …" if delay_before_next else "giving up.")
                )
                if delay_before_next is not None:
                    await asyncio.sleep(delay_before_next)

        raise last_error  # type: ignore[misc]

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


class FireworksChatProvider:
    """Fireworks.ai chat via OpenAI-compatible API. Used for 'private' mode."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "accounts/fireworks/models/qwen2p5-vl-32b-instruct",
        base_url: str = "https://api.fireworks.ai/inference/v1",
        default_temperature: float = 0.0,
        default_max_tokens: int = 4096,
    ):
        self._api_key = api_key
        self._default_model = default_model
        # Strip trailing /chat/completions if included — AsyncOpenAI appends that itself
        self._base_url = base_url.rstrip("/").removesuffix("/chat/completions")
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
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
        target_model = model or self._default_model
        client = self._get_client()

        # Convert to OpenAI message format; inject system if provided
        oai_messages: list[dict[str, Any]] = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        for m in messages:
            if m.role == "system":
                # Already handled above; skip duplicates
                continue
            oai_messages.append({"role": m.role, "content": m.content})

        kwargs: dict[str, Any] = {
            "model": target_model,
            "messages": oai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        if response_format is not None:
            kwargs["response_format"] = response_format

        start = time.perf_counter()
        try:
            if stream:
                return self._stream_chat(client, kwargs, target_model, start)
            response = await client.chat.completions.create(**kwargs)
            latency_ms = (time.perf_counter() - start) * 1000
            content = response.choices[0].message.content or "" if response.choices else ""
            u = Usage(
                provider="fireworks",
                model=target_model,
                prompt_tokens=getattr(response.usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(response.usage, "completion_tokens", 0) or 0,
                total_tokens=getattr(response.usage, "total_tokens", 0) or 0,
                latency_ms=latency_ms,
                request_id=getattr(response, "id", None),
            )
            return ChatResult(content=content, usage=u, finish_reason="stop")
        except Exception as e:
            if isinstance(e, ModelProviderError):
                raise
            raise _normalize_openai_error(e)

    async def _stream_chat(
        self,
        client: Any,
        kwargs: dict[str, Any],
        model: str,
        start: float,
    ) -> AsyncIterator[StreamChunk]:
        try:
            stream = await client.chat.completions.create(**kwargs)
            async for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                if choice is None:
                    continue
                delta_content = getattr(choice.delta, "content", None)
                if delta_content:
                    yield StreamChunk(content_delta=delta_content)
                if getattr(choice, "finish_reason", None) == "stop":
                    latency_ms = (time.perf_counter() - start) * 1000
                    u = Usage(
                        provider="fireworks",
                        model=model,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        latency_ms=latency_ms,
                    )
                    yield StreamChunk(content_delta="", usage=u, finish_reason="stop")
        except Exception as e:
            if isinstance(e, ModelProviderError):
                raise
            raise _normalize_openai_error(e)


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
