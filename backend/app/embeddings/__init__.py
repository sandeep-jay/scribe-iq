"""Query embedding helpers with provider-backed implementations."""

from __future__ import annotations

from app.config import get_settings
from app.embeddings.errors import EmbeddingConfigurationError, EmbeddingProviderError
from app.embeddings.provider import EmbeddingProvider, get_embedding_provider
from app.embeddings.types import EmbeddingResult

__all__ = [
    "EmbeddingConfigurationError",
    "EmbeddingProvider",
    "EmbeddingProviderError",
    "EmbeddingResult",
    "compose_note_embed_input",
    "embed_and_vector_literal",
    "embed_query_text",
    "get_embedding_provider",
    "vector_literal",
]


def vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{float(x):.8f}" for x in vec) + "]"


def _validate_embedding_dimensions(result: EmbeddingResult) -> None:
    settings = get_settings()
    if settings.embed_dim and result.dimensions != settings.embed_dim:
        raise EmbeddingConfigurationError(
            f"Embedding length {result.dimensions} from {result.provider}/{result.model} "
            f"does not match EMBED_DIM={settings.embed_dim}; use a matching model or migrate/re-embed."
        )


async def embed_query_text(text: str) -> tuple[list[float], str]:
    """Return raw embedding vector and pgvector literal for SQL."""
    settings = get_settings()
    provider = get_embedding_provider(settings)
    result = await provider.embed_text(text)
    _validate_embedding_dimensions(result)
    return result.vector, vector_literal(result.vector)


def compose_note_embed_input(structured_note: dict, conversation_text: str | None) -> str:
    """Match corpus embedding text shape (subset of loader logic)."""
    sn = structured_note if isinstance(structured_note, dict) else {}
    summary = str(sn.get("summary") or "").strip()
    full_note = str(sn.get("full_note") or "").strip()
    conv = (conversation_text or "").strip()
    parts: list[str] = []
    if summary:
        parts.append(summary)
    if conv:
        parts.append(conv[:6000])
    if full_note:
        parts.append(full_note[:8000])
    out = "\n\n".join(parts)
    max_chars = 30_000
    if len(out) > max_chars:
        out = out[: max_chars - 3] + "..."
    out_st = out.strip()
    return out_st if out_st else "(empty)"


async def embed_and_vector_literal(for_embedding: str) -> str | None:
    """Embed arbitrary chunk; returns None when embeddings are not configured."""
    try:
        _, lit = await embed_query_text(for_embedding)
        return lit
    except RuntimeError:
        return None
