"""Unit tests for ModelProvider (chat, embed, exceptions, streaming). Vendor SDKs are mocked."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lib.model_provider.exceptions import AuthError, InvalidRequestError, RateLimitError
from lib.model_provider.providers import AnthropicChatProvider, OpenAIProvider
from lib.model_provider.types import ChatMessage, Usage


# ---- Chat: returns text + usage ----
@pytest.mark.asyncio
async def test_chat_returns_text_and_usage():
    """Chat (non-streaming) returns content and usage info."""
    mock_usage = MagicMock()
    mock_usage.input_tokens = 10
    mock_usage.output_tokens = 5
    mock_block = MagicMock()
    mock_block.text = "Hello back"
    mock_response = MagicMock()
    mock_response.usage = mock_usage
    mock_response.content = [mock_block]
    mock_response.id = "msg_123"

    client = MagicMock()
    client.messages.create = AsyncMock(return_value=mock_response)

    provider = AnthropicChatProvider(api_key="test-key", default_model="claude-test")
    provider._client = client

    messages = [ChatMessage(role="user", content="Hello")]
    result = await provider.chat(messages, stream=False)

    assert result.content == "Hello back"
    assert result.usage.provider == "anthropic"
    assert result.usage.model == "claude-test"
    assert result.usage.prompt_tokens == 10
    assert result.usage.completion_tokens == 5
    assert result.usage.total_tokens == 15
    assert result.usage.latency_ms >= 0
    assert result.usage.request_id == "msg_123"


# ---- Embed: returns vectors + usage ----
@pytest.mark.asyncio
async def test_embed_returns_vectors_and_usage():
    """Embed returns list of vectors and usage info."""
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 2
    mock_usage.total_tokens = 2
    mock_response = MagicMock()
    mock_response.usage = mock_usage
    mock_response.data = [
        MagicMock(embedding=[0.1] * 4),
        MagicMock(embedding=[0.2] * 4),
    ]
    mock_response.id = "emb_456"

    client = MagicMock()
    client.embeddings.create = AsyncMock(return_value=mock_response)

    provider = OpenAIProvider(api_key="test-key", default_embed_model="text-embedding-3-small")
    provider._client = client

    result = await provider.embed(["a", "b"])

    assert len(result.embeddings) == 2
    assert result.embeddings[0] == [0.1] * 4
    assert result.embeddings[1] == [0.2] * 4
    assert result.usage.provider == "openai"
    assert result.usage.model == "text-embedding-3-small"
    assert result.usage.prompt_tokens == 2
    assert result.usage.total_tokens == 2
    assert result.usage.latency_ms >= 0
    assert result.usage.request_id == "emb_456"


# ---- Exceptions normalized ----
@pytest.mark.asyncio
async def test_anthropic_429_raises_rate_limit_error():
    """Anthropic 429 is normalized to RateLimitError."""
    client = MagicMock()
    err = Exception("Rate limit exceeded")
    err.response = MagicMock()
    err.response.status_code = 429
    err.response.text = "rate limit"
    client.messages.create = AsyncMock(side_effect=err)

    provider = AnthropicChatProvider(api_key="test")
    provider._client = client

    with pytest.raises(RateLimitError) as exc_info:
        await provider.chat([ChatMessage(role="user", content="Hi")], stream=False)
    assert "429" in str(exc_info.value.vendor_payload.get("status_code", ""))


@pytest.mark.asyncio
async def test_anthropic_401_raises_auth_error():
    """Anthropic 401 is normalized to AuthError."""
    client = MagicMock()
    err = Exception("Invalid API key")
    err.response = MagicMock()
    err.response.status_code = 401
    err.response.text = "invalid"
    client.messages.create = AsyncMock(side_effect=err)

    provider = AnthropicChatProvider(api_key="test")
    provider._client = client

    with pytest.raises(AuthError):
        await provider.chat([ChatMessage(role="user", content="Hi")], stream=False)


@pytest.mark.asyncio
async def test_openai_invalid_request_raises_invalid_request_error():
    """OpenAI 400-style error is normalized to InvalidRequestError."""
    client = MagicMock()
    err = Exception("Invalid request")
    err.status_code = 400
    err.response = MagicMock()
    err.response.status_code = 400
    err.response.text = "bad request"
    client.embeddings.create = AsyncMock(side_effect=err)

    provider = OpenAIProvider(api_key="test")
    provider._client = client

    with pytest.raises(InvalidRequestError):
        await provider.embed(["text"])


# ---- Streaming yields chunks ----
@pytest.mark.asyncio
async def test_chat_stream_yields_chunks_with_usage_on_final():
    """Streaming chat yields content deltas and usage on final chunk."""
    # Simulate stream events: content_block_delta (text), message_delta (usage), message_stop
    class StreamCtx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def __aiter__(self):
            delta = MagicMock()
            delta.text = "Hello"
            yield type("Event", (), {"type": "content_block_delta", "delta": delta})()
            delta2 = MagicMock()
            delta2.text = " world"
            yield type("Event", (), {"type": "content_block_delta", "delta": delta2})()
            u = MagicMock()
            u.input_tokens = 2
            u.output_tokens = 2
            d = MagicMock()
            d.usage = u
            yield type("Event", (), {"type": "message_delta", "delta": d})()
            yield type("Event", (), {"type": "message_stop"})()

    def fake_stream(**kwargs):
        return StreamCtx()

    client = MagicMock()
    client.messages.stream = fake_stream

    provider = AnthropicChatProvider(api_key="test", default_model="claude-test")
    provider._client = client

    messages = [ChatMessage(role="user", content="Hi")]
    stream_result = await provider.chat(messages, stream=True)

    chunks = []
    async for ch in stream_result:
        chunks.append(ch)

    assert len(chunks) >= 2
    texts = [c.content_delta for c in chunks if c.content_delta]
    assert "Hello" in texts
    assert " world" in texts
    # One chunk should have usage (message_stop after message_delta)
    usage_chunks = [c for c in chunks if c.usage is not None]
    assert len(usage_chunks) >= 1
    assert usage_chunks[0].usage.provider == "anthropic"
    assert usage_chunks[0].usage.prompt_tokens == 2
    assert usage_chunks[0].usage.completion_tokens == 2
