"""Embedding provider exceptions."""


class EmbeddingConfigurationError(RuntimeError):
    """Missing or invalid embedding configuration."""


class EmbeddingProviderError(RuntimeError):
    """Upstream embedding provider failure."""
