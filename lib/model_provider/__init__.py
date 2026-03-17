"""ModelProvider: single interface for LLM chat and embeddings. No direct vendor SDK usage outside this package."""

from lib.model_provider.config import get_model_provider, get_model_provider_for_mode, chat, embed
from lib.model_provider.exceptions import (
    AuthError,
    InvalidRequestError,
    ModelProviderError,
    ProviderError,
    RateLimitError,
)
from lib.model_provider.langchain_bridge import ModelProviderChatModel, ModelProviderEmbeddings
from lib.model_provider.sparse_embeddings import ModelProviderSparseEmbeddings
from lib.model_provider.types import (
    ChatMessage,
    ChatResult,
    EmbedResult,
    StreamChunk,
    Usage,
)

__all__ = [
    "get_model_provider",
    "get_model_provider_for_mode",
    "chat",
    "embed",
    "ModelProviderChatModel",
    "ModelProviderEmbeddings",
    "ModelProviderSparseEmbeddings",
    "ModelProviderError",
    "RateLimitError",
    "AuthError",
    "InvalidRequestError",
    "ProviderError",
    "Usage",
    "ChatMessage",
    "ChatResult",
    "EmbedResult",
    "StreamChunk",
]
