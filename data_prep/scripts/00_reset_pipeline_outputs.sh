#!/usr/bin/env bash
#
# Operational logging: ``log_info`` / ``log_warn`` / ``log_error`` write to stderr so stdout
# stays empty unless you intentionally echo banners (see final ✓ lines below).
#
# Drop derived pipeline artifacts so 02–09 can run cleanly after e.g. Synthea regen.
# Keeps: data/raw/synthea/csv, HF / AGBonnet exports, Athena vocabulary, most staging seeds.
set -euo pipefail

log_info() { echo "[INFO] $(basename "$0"): $*" >&2; }
log_warn() { echo "[WARN] $(basename "$0"): $*" >&2; }
log_error() { echo "[ERROR] $(basename "$0"): $*" >&2; }

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
      log_info "Usage: $0 [--corpus]"
      log_info "  --corpus  Also remove data/clinical_corpus_v1 and data/clinical_corpus_v2"
      exit 0
      ;;
    *)
      log_error "Unknown option: $1"
      exit 1
      ;;
  esac
done

log_info "reset_pipeline_outputs_started repo=${REPO_ROOT} corpus_flag=${CORPUS}"

rm -f \
  "$STAGING/note_pool.jsonl" \
  "$STAGING/match_results.jsonl" \
  "$STAGING/aci_reservations.jsonl" \
  "$STAGING/adapted_notes.jsonl" \
  "$STAGING/selected_patients.jsonl"

if [[ "$CORPUS" -eq 1 ]]; then
  rm -rf "$REPO_ROOT/data/clinical_corpus_v1" "$REPO_ROOT/data/clinical_corpus_v2"
fi

log_info "reset_pipeline_outputs_succeeded removed=staging_core_artifacts"
[[ "$CORPUS" -eq 1 ]] && log_info "reset_pipeline_outputs_succeeded removed=clinical_corpus_dirs"
log_info "reset_pipeline_outputs_note raw_synthea_and_most_staging_untouched"
