"""Create pgvector ivfflat index for notes.embedding retrieval."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260506_005"
down_revision = "20260506_004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ANN index for cosine-distance retrieval in /chat.
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_notes_embedding_ivfflat_cosine
            ON notes USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_notes_embedding_ivfflat_cosine"))
