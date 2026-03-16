from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from langchain_core.messages import HumanMessage, AIMessage


@pytest.mark.asyncio
async def test_save_thread_metadata_new_key():
    """First write: entry is prepended and TTL is set."""
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)
    mock_redis.lpush = AsyncMock()
    mock_redis.ltrim = AsyncMock()
    mock_redis.expire = AsyncMock()

    with patch("api.index._get_redis", return_value=mock_redis):
        from api.index import _save_thread_metadata
        await _save_thread_metadata("user-1", "thread-abc", "Hello world, this is my first message")

    mock_redis.lpush.assert_called_once()
    args = mock_redis.lpush.call_args[0]
    assert args[0] == "threads:user-1"
    entry = json.loads(args[1])
    assert entry["threadId"] == "thread-abc"
    assert entry["title"] == "Hello world, this is my first message"
    assert "createdAt" in entry
    mock_redis.expire.assert_called_once_with("threads:user-1", 864_000)


@pytest.mark.asyncio
async def test_save_thread_metadata_existing_key_no_expire():
    """Subsequent writes: entry prepended but TTL not reset."""
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=1)
    mock_redis.lpush = AsyncMock()
    mock_redis.ltrim = AsyncMock()
    mock_redis.expire = AsyncMock()

    with patch("api.index._get_redis", return_value=mock_redis):
        from api.index import _save_thread_metadata
        await _save_thread_metadata("user-1", "thread-xyz", "Another message")

    mock_redis.expire.assert_not_called()


@pytest.mark.asyncio
async def test_save_thread_metadata_truncates_title():
    """Title is truncated to 60 chars."""
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=1)
    mock_redis.lpush = AsyncMock()
    mock_redis.ltrim = AsyncMock()
    mock_redis.expire = AsyncMock()

    long_msg = "A" * 100
    with patch("api.index._get_redis", return_value=mock_redis):
        from api.index import _save_thread_metadata
        await _save_thread_metadata("user-1", "thread-xyz", long_msg)

    args = mock_redis.lpush.call_args[0]
    entry = json.loads(args[1])
    assert len(entry["title"]) == 60


@pytest.mark.asyncio
async def test_list_threads_returns_entries():
    entries = [
        json.dumps({"threadId": "t1", "title": "Hello", "createdAt": "2026-03-16T10:00:00+00:00"}),
        json.dumps({"threadId": "t2", "title": "World", "createdAt": "2026-03-15T10:00:00+00:00"}),
    ]
    mock_redis = AsyncMock()
    mock_redis.lrange = AsyncMock(return_value=entries)

    with patch("api.index._get_redis", return_value=mock_redis):
        from api.index import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/app/chat/threads?user_id=user-1")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["threads"]) == 2
    assert data["threads"][0]["threadId"] == "t1"


@pytest.mark.asyncio
async def test_list_threads_missing_key_returns_empty():
    mock_redis = AsyncMock()
    mock_redis.lrange = AsyncMock(return_value=[])

    with patch("api.index._get_redis", return_value=mock_redis):
        from api.index import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/app/chat/threads?user_id=nobody")

    assert resp.status_code == 200
    assert resp.json() == {"threads": []}


@pytest.mark.asyncio
async def test_get_thread_messages_found():
    snapshot = MagicMock()
    snapshot.config = {"configurable": {"checkpoint_id": "ckpt-1"}}
    snapshot.values = {
        "messages": [
            HumanMessage(content="What is my tax residency?"),
            AIMessage(content="Based on the rules, you may be a tax resident if..."),
        ]
    }

    mock_graph = AsyncMock()
    mock_graph.aget_state = AsyncMock(return_value=snapshot)

    with patch("api.index.get_graph", return_value=mock_graph):
        from api.index import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/app/chat/threads/thread-123/messages")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["messages"]) == 2
    assert data["messages"][0] == {"role": "user", "content": "What is my tax residency?"}
    assert data["messages"][1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_get_thread_messages_not_found():
    snapshot = MagicMock()
    snapshot.config = {"configurable": {}}  # no checkpoint_id
    snapshot.values = {}

    mock_graph = AsyncMock()
    mock_graph.aget_state = AsyncMock(return_value=snapshot)

    with patch("api.index.get_graph", return_value=mock_graph):
        from api.index import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/app/chat/threads/nonexistent/messages")

    assert resp.status_code == 404
