#!/bin/bash
# Run from repo root or anywhere; resolves paths relative to this script.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
JAR="$REPO_ROOT/synthea-with-dependencies.jar"
OUTPUT_DIR="$REPO_ROOT/data/raw/synthea"

if [ ! -f "$JAR" ]; then
  echo "ERROR: synthea-with-dependencies.jar not found at $JAR"
  echo "Download from: https://github.com/synthetichealth/synthea/releases"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

# CSV exporter: emit every table Synthea supports (conditions, medications, claims, …).
# Upstream default synthea.properties excludes only patient_expenses.csv; clearing
# excluded_files includes that file too. The Python pipeline only reads five of these
# (see utils/synthea_utils.load_synthea); other CSVs are harmless extras.
java -jar "$JAR" \
  -p 1000 \
  -s 42 \
  --exporter.csv.export true \
  --exporter.csv.excluded_files= \
  --exporter.fhir.export false \
  --exporter.baseDirectory "$OUTPUT_DIR"
# Do not pass obsolete -m names: mismatched module IDs load zero modules, so CSVs lack
# conditions/medications/procedures. Default run loads the full bundled module set; -s
# still fixes the population RNG for reproducibility (same JAR + settings).

echo ""
echo "✓ Synthea generation complete"
echo "  Output: $OUTPUT_DIR/csv/"
ls -lh "$OUTPUT_DIR/csv/" || true
