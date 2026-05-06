"""Add composite indexes for patient meeting-prep hot queries."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260506_004"
down_revision = "20260505_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Speeds notes lookups used by meeting_prep_context_bundle and notes_fingerprint.
    op.create_index(
        "ix_notes_patient_domain_session_created",
        "notes",
        ["patient_id", "domain", "session_date", "created_at"],
    )

    # Partial index avoids scanning rows without longitudinal payload for the "latest rich context" lookup.
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_notes_patient_domain_longitudinal_recent
            ON notes (patient_id, domain, session_date DESC, created_at DESC)
            WHERE longitudinal_context IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_notes_patient_domain_longitudinal_recent"))
    op.drop_index("ix_notes_patient_domain_session_created", table_name="notes")
