"""Query embedding helpers (OpenAI API; aligns with corpus loader dims)."""

from __future__ import annotations

from app.config import get_settings


def vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{float(x):.8f}" for x in vec) + "]"


async def embed_query_text(text: str) -> tuple[list[float], str]:
    """Return raw embedding vector and pgvector literal for SQL."""
    settings = get_settings()
    if settings.embedding_provider == "none" or not (settings.openai_api_key or "").strip():
        msg = (
            "Embeddings unavailable: set OPENAI_API_KEY and embedding_provider "
            "(e.g. openai), then run scribe-load-corpus --embed."
        )
        raise RuntimeError(msg)

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    kwargs: dict[str, object] = {
        "model": settings.openai_embeddings_model,
        "input": [text.strip()],
    }
    if settings.openai_embeddings_dimensions is not None:
        kwargs["dimensions"] = settings.openai_embeddings_dimensions

    resp = await client.embeddings.create(**kwargs)  # type: ignore[arg-type]
    if not resp.data:
        raise RuntimeError("embedding API returned no data")

    vec = list(resp.data[0].embedding)
    if settings.embed_dim and len(vec) != settings.embed_dim:
        raise RuntimeError(
            f"Embedding length {len(vec)} does not match embed_dim={settings.embed_dim}; "
            "check openai_embeddings_model / dimensions vs migration vector(N)."
        )
    return vec, vector_literal(vec)


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
