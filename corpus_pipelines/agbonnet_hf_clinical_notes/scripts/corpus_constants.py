"""Shared defaults for HF clinical corpus prep (Phase 0)."""

DEFAULT_DATASET_ID = "AGBonnet/augmented-clinical-notes"

# Canonical column names for Phase 1 loader contract (after Task 0 validation).
# Adjust if validate_dataset / staging reports differ.
CANONICAL_TRANSCRIPT_COLUMN = "conversation"
CANONICAL_REFERENCE_NOTE_COLUMN = "note"
CANONICAL_FULL_NOTE_COLUMN = "full_note"
CANONICAL_SUMMARY_JSON_COLUMN = "summary"
