#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="$ROOT_DIR/snacdb_antigen_compare"
LOG_DIR="$OUT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/run_all.log"
exec > >(tee -a "$LOG_FILE") 2>&1

INPUT_XLSX="${1:-${SNACDB_INPUT_XLSX:-$ROOT_DIR/INPUT_ANTIGENS.xlsx}}"

echo "[plan] Step 1/6: Inspecting workbook and generating normalized manifests from $INPUT_XLSX..."
python "$OUT_DIR/scripts/inspect_excel.py" "$INPUT_XLSX" "$OUT_DIR"

echo "[plan] Step 2/6: Resolving representative query structures conservatively..."
python "$OUT_DIR/scripts/resolve_query_structures.py" "$OUT_DIR/01_manifest/antigen_manifest_normalized.csv" "$OUT_DIR/02_queries/query_structure_manifest.csv"

echo "[plan] Step 3/6: Downloading selected query structures..."
python "$OUT_DIR/scripts/download_query_structures.py" "$OUT_DIR/02_queries/query_structure_manifest.csv" "$OUT_DIR/02_queries/structures" "$OUT_DIR/logs/query_structure_downloads.log"

echo "[plan] Step 4/6: Recording SNAC-DB reference provenance (download optional)..."
python "$OUT_DIR/scripts/download_snacdb_reference.py" "$OUT_DIR/reference/snacdb_curated" "$OUT_DIR/reference/REFERENCE_SOURCE.txt"

echo "[plan] Step 5/6: Running SNAC-DB antigen-mode hit search if inputs are available..."
if compgen -G "$OUT_DIR/02_queries/structures/*" > /dev/null && compgen -G "$OUT_DIR/reference/snacdb_curated/all_complexes/*" > /dev/null; then
  bash "$OUT_DIR/scripts/run_antigen_hits.sh" "$OUT_DIR/reference/snacdb_curated/all_complexes" "$OUT_DIR/02_queries/structures"
else
  echo "Skipping SNAC-DB hit search because the query structure directory or reference dataset directory is empty."
fi

echo "[plan] Step 6/6: Postprocessing outputs and writing the summary report..."
python "$OUT_DIR/scripts/postprocess_snacdb_hits.py" "$OUT_DIR"
python "$OUT_DIR/scripts/write_summary_report.py" "$OUT_DIR" "$INPUT_XLSX"

echo "[done] Workflow finished. Review $OUT_DIR/README.md for rerun instructions."
