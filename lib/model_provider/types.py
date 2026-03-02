"""Structured types for model provider API and usage tracking."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Usage:
    """Usage info for a single call (for audits/evals)."""

    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    request_id: str | None = None


@dataclass
class ChatMessage:
    """Single message in a chat request."""

    role: str  # "user" | "assistant" | "system"
    content: str | list[dict[str, Any]]


@dataclass
class ChatResult:
    """Non-streaming chat response."""

    content: str
    usage: Usage
    finish_reason: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class StreamChunk:
    """Streaming chat chunk. Final chunk carries usage; intermediate chunks have usage=None."""

    content_delta: str
    usage: Usage | None = None
    finish_reason: str | None = None


@dataclass
class EmbedResult:
    """Embedding response."""

    embeddings: list[list[float]]
    usage: Usage
