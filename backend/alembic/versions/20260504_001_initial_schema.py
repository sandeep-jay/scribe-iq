"""Initial patients + notes tables with pgvector embedding column."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID


revision = "20260504_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text('CREATE EXTENSION IF NOT EXISTS "vector"'))

    op.create_table(
        "patients",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("domain", sa.Text(), nullable=False, server_default=sa.text("'clinical'")),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("external_id", name="uq_patients_external_id"),
    )

    op.create_index("ix_patients_domain", "patients", ["domain"])
    op.create_index("ix_patients_metadata_gin", "patients", ["metadata"], postgresql_using="gin")

    op.create_table(
        "notes",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "patient_id",
            UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("domain", sa.Text(), nullable=False, server_default=sa.text("'clinical'")),
        sa.Column("external_encounter_id", sa.Text(), nullable=False),
        sa.Column("corpus_note_id", sa.Text(), nullable=True),
        sa.Column("conversation_text", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "structured_note",
            JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "entity_payload",
            JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("longitudinal_context", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("specialty", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default=sa.text("'dataset'")),
        sa.Column("session_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "external_encounter_id",
            name="uq_notes_external_encounter_id",
        ),
    )

    op.create_index("ix_notes_patient_id", "notes", ["patient_id"])
    op.create_index("ix_notes_domain", "notes", ["domain"])
    op.create_index("ix_notes_specialty", "notes", ["specialty"])

    op.execute(sa.text("ALTER TABLE notes ADD COLUMN embedding vector(1536)"))
    # Vector index intentionally deferred until after embeddings are loaded (recommended by pgvector;
    # also keeps empty DB migrations deterministic). Apply in a follow-up migration or DDL script.


def downgrade() -> None:
    op.drop_table("notes")
    op.drop_table("patients")
    op.execute(sa.text('DROP EXTENSION IF EXISTS "vector"'))
