#!/usr/bin/env bash
# Drop derived pipeline artifacts so 02–09 can run cleanly after e.g. Synthea regen.
# Keeps: data/raw/synthea/csv, HF / AGBonnet exports, Athena vocabulary, most staging seeds.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STAGING="$REPO_ROOT/data/staging"

CORPUS=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --corpus)
      CORPUS=1
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--corpus]"
      echo "  --corpus  Also remove data/clinical_corpus_v1 and data/clinical_corpus_v2"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

rm -f \
  "$STAGING/note_pool.jsonl" \
  "$STAGING/match_results.jsonl" \
  "$STAGING/aci_reservations.jsonl" \
  "$STAGING/adapted_notes.jsonl" \
  "$STAGING/selected_patients.jsonl"

if [[ "$CORPUS" -eq 1 ]]; then
  rm -rf "$REPO_ROOT/data/clinical_corpus_v1" "$REPO_ROOT/data/clinical_corpus_v2"
fi

echo "✓ Removed core staging build artifacts."
[[ "$CORPUS" -eq 1 ]] && echo "✓ Removed clinical_corpus_v1 / clinical_corpus_v2 (if present)."
echo "  Raw Synthea CSVs and seeds under data/raw/ and most of data/staging/ are untouched."
