"""Provider-layer exceptions mapped to HTTP responses in API routes."""


class LlmConfigurationError(RuntimeError):
    """Missing or invalid provider configuration (maps to HTTP 503)."""


class LlmProviderError(RuntimeError):
    """Upstream provider failure (maps to HTTP 502)."""


class LlmJsonModeError(RuntimeError):
    """JSON contract failure from provider output (maps to HTTP 502)."""
