"""Append-only audit trail for AI interactions (Responsible AI Control Center)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID

revision = "20260505_003"
down_revision = "20260504_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_interactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("interaction_type", sa.Text(), nullable=False),
        sa.Column("patient_id", sa.Text(), nullable=True),
        sa.Column("note_id", sa.Text(), nullable=True),
        sa.Column("model_provider", sa.Text(), nullable=True),
        sa.Column("model_name", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=True),
        sa.Column("system_prompt_hash", sa.Text(), nullable=True),
        sa.Column("input_hash", sa.Text(), nullable=True),
        sa.Column("output_hash", sa.Text(), nullable=True),
        sa.Column("input_redacted_preview", sa.Text(), nullable=True),
        sa.Column("output_redacted_preview", sa.Text(), nullable=True),
        sa.Column("retrieved_sources_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("citations_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("safety_flags_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("governance_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_ai_interactions_created_at",
        "ai_interactions",
        ["created_at"],
        postgresql_ops={"created_at": "DESC"},
    )
    op.create_index("ix_ai_interactions_type", "ai_interactions", ["interaction_type"])
    op.create_index("ix_ai_interactions_patient", "ai_interactions", ["patient_id"])
    op.create_index("ix_ai_interactions_status", "ai_interactions", ["status"])


def downgrade() -> None:
    op.drop_table("ai_interactions")
