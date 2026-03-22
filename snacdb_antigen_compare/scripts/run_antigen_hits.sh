#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="$ROOT_DIR/snacdb_antigen_compare"
LOG_DIR="$OUT_DIR/logs"
RAW_DIR="$OUT_DIR/03_raw_results"
mkdir -p "$LOG_DIR" "$RAW_DIR"
LOG_FILE="$LOG_DIR/run_antigen_hits.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "[plan] Running SNAC-DB antigen-mode structural hit search..."
REFERENCE_DIR="${1:-$OUT_DIR/reference/snacdb_curated}"
QUERY_DIR="${2:-$OUT_DIR/02_queries/structures}"
SNACDB_DIR="$ROOT_DIR/external/SNAC-DB"

if [[ ! -d "$SNACDB_DIR" ]]; then
  echo "ERROR: SNAC-DB repo missing at $SNACDB_DIR; run setup_snacdb.sh first." >&2
  exit 1
fi
if [[ ! -d "$QUERY_DIR" ]]; then
  echo "ERROR: Query structure directory missing: $QUERY_DIR" >&2
  exit 1
fi
if [[ ! -d "$REFERENCE_DIR" ]]; then
  echo "ERROR: Reference directory missing: $REFERENCE_DIR" >&2
  exit 1
fi
if ! compgen -G "$QUERY_DIR/*" > /dev/null; then
  echo "ERROR: No query structures found in $QUERY_DIR" >&2
  exit 1
fi
if ! compgen -G "$REFERENCE_DIR/*" > /dev/null; then
  echo "ERROR: Reference directory is empty: $REFERENCE_DIR" >&2
  exit 1
fi

cd "$ROOT_DIR"
bash "$SNACDB_DIR/finding_hits.sh" "$REFERENCE_DIR" antigen "$QUERY_DIR" False

REPORT_PATH="$(find "$(dirname "$REFERENCE_DIR")" -maxdepth 1 -type f -name "$(basename "$REFERENCE_DIR")_antigen_*_report" | head -n 1 || true)"
if [[ -n "$REPORT_PATH" ]]; then
  cp "$REPORT_PATH" "$RAW_DIR/foldseek_report.tsv"
  echo "Copied Foldseek report to $RAW_DIR/foldseek_report.tsv"
else
  echo "WARNING: no Foldseek report found after SNAC-DB run." >&2
fi
