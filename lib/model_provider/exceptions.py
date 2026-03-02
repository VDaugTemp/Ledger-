"""Normalized exceptions for model provider calls. Original vendor payload is kept for logs, not exposed."""

from typing import Any


class ModelProviderError(Exception):
    """Base exception for model provider errors."""

    def __init__(self, message: str, *, vendor_payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.vendor_payload = vendor_payload or {}


class RateLimitError(ModelProviderError):
    """Provider rate limit exceeded (429 or similar)."""


class AuthError(ModelProviderError):
    """Invalid or missing API key / authentication."""


class InvalidRequestError(ModelProviderError):
    """Bad request (invalid params, model not found, etc.)."""


class ProviderError(ModelProviderError):
    """Generic provider or network error."""
