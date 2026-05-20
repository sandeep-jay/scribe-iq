#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CORPUS="$ROOT/data/clinical_corpus_v2"
required=(patients.jsonl encounters.jsonl notes.jsonl manifest.json)
missing=()

for f in "${required[@]}"; do
  [[ -f "$CORPUS/$f" ]] || missing+=("$f")
done

if (( ${#missing[@]} )); then
  echo "Corpus artifact missing: ${missing[*]}"
  echo "See docs/guides/CORPUS_ARTIFACTS.md"
  echo "See data_prep/README.md"
  exit 0
fi

echo "Corpus artifact present at $CORPUS"
