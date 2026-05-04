"""Patient-level cached meeting prep summary (Groq-generated)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

revision = "20260504_002"
down_revision = "20260504_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_meeting_prep",
        sa.Column("patient_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("domain", sa.Text(), nullable=False, server_default=sa.text("'clinical'")),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("prompt_version", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("source_fingerprint", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "generated_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_patient_meeting_prep_domain", "patient_meeting_prep", ["domain"])


def downgrade() -> None:
    op.drop_table("patient_meeting_prep")
