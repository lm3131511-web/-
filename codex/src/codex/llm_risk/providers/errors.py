from __future__ import annotations


class ProviderError(Exception):
    """Base class for provider exceptions."""


class ProviderTransportError(ProviderError):
    """Raised when the HTTP transport fails."""


class ProviderResponseError(ProviderError):
    """Raised when the provider returns an invalid payload."""
