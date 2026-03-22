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
REFERENCE_DIR="$(realpath "${1:-$OUT_DIR/reference/snacdb_curated/all_complexes}")"
QUERY_DIR="$(realpath "${2:-$OUT_DIR/02_queries/structures}")"
SNACDB_DIR="$ROOT_DIR/external/SNAC-DB"
FOLDSEEK_BIN="$ROOT_DIR/tools/foldseek/bin"
REFERENCE_PARENT="$(dirname "$REFERENCE_DIR")"
REFERENCE_BASENAME="$(basename "$REFERENCE_DIR")"
REFERENCE_QUERY_DIR="$REFERENCE_PARENT/${REFERENCE_BASENAME}_antigen_query"
RESULT_PREFIX="$REFERENCE_PARENT/${REFERENCE_BASENAME}_antigen_$(basename "$QUERY_DIR")"
TMP_DIR="$RAW_DIR/tmp_search_single"

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

if [[ -d "$FOLDSEEK_BIN" ]]; then
  export PATH="$FOLDSEEK_BIN:$PATH"
fi
if ! command -v foldseek >/dev/null 2>&1; then
  echo "ERROR: foldseek binary not found. Expected bundled install at $FOLDSEEK_BIN or a system install on PATH." >&2
  exit 1
fi

cd "$ROOT_DIR"
echo "[plan] Preparing antigen-chain reference directory via SNAC-DB testdata_setup.py..."
if [[ -d "$REFERENCE_QUERY_DIR" ]] && compgen -G "$REFERENCE_QUERY_DIR/*" > /dev/null; then
  echo "[plan] Reusing existing prepared antigen-chain reference directory: $REFERENCE_QUERY_DIR"
else
  python "$SNACDB_DIR/src/testdata_setup.py" -q "$REFERENCE_DIR" -k "${REFERENCE_BASENAME}_antigen" -s ag_chains > "$REFERENCE_PARENT/Setup_Directory_log" 2>&1
fi

if [[ ! -d "$REFERENCE_QUERY_DIR" ]]; then
  echo "ERROR: Expected antigen-chain reference directory was not created: $REFERENCE_QUERY_DIR" >&2
  exit 1
fi

echo "[plan] Running Foldseek multimer search against prepared antigen-chain reference structures..."
rm -f "${RESULT_PREFIX}" "${RESULT_PREFIX}.dbtype" "${RESULT_PREFIX}.index" "${RESULT_PREFIX}.lookup" "${RESULT_PREFIX}.source"
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"
foldseek easy-multimersearch "$QUERY_DIR" "$REFERENCE_QUERY_DIR" "$RESULT_PREFIX" "$TMP_DIR" > "$REFERENCE_PARENT/foldseek_search_log" 2>&1

REPORT_PATH="$(find "$REFERENCE_PARENT" -maxdepth 1 -type f -name "$(basename "$RESULT_PREFIX")_report" | head -n 1 || true)"
if [[ -n "$REPORT_PATH" ]]; then
  cp "$REPORT_PATH" "$RAW_DIR/foldseek_report.tsv"
  echo "Copied Foldseek report to $RAW_DIR/foldseek_report.tsv"
else
  echo "WARNING: no Foldseek report found after SNAC-DB run." >&2
fi
