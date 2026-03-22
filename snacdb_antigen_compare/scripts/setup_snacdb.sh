#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="$ROOT_DIR/snacdb_antigen_compare"
LOG_DIR="$OUT_DIR/logs"
mkdir -p "$LOG_DIR" "$ROOT_DIR/external"
LOG_FILE="$LOG_DIR/setup_snacdb.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "[plan] Setting up reproducible SNAC-DB environment and dependencies..."
cd "$ROOT_DIR"

if [[ ! -d external/SNAC-DB/.git ]]; then
  git clone https://github.com/Sanofi-Public/SNAC-DB.git external/SNAC-DB
else
  echo "SNAC-DB repository already present at external/SNAC-DB"
fi

ENV_YML="$OUT_DIR/env/environment.yml"
ENV_NAME="snacdb_antigen_compare"
if command -v micromamba >/dev/null 2>&1; then
  micromamba create -y -f "$ENV_YML"
  eval "$(micromamba shell hook --shell bash)"
  micromamba activate "$ENV_NAME"
elif command -v mamba >/dev/null 2>&1; then
  mamba env create -f "$ENV_YML" || mamba env update -f "$ENV_YML"
  source "$(conda info --base)/etc/profile.d/conda.sh"
  conda activate "$ENV_NAME"
elif command -v conda >/dev/null 2>&1; then
  conda env create -f "$ENV_YML" || conda env update -f "$ENV_YML"
  source "$(conda info --base)/etc/profile.d/conda.sh"
  conda activate "$ENV_NAME"
else
  echo "ERROR: conda/mamba/micromamba not found; install one of them before running setup." >&2
  exit 1
fi

python -m pip install --upgrade pip
python -m pip install -r external/SNAC-DB/requirements.txt
python -m pip install git+https://github.com/oxpig/ANARCI.git
python -m pip install -e external/SNAC-DB
snacdb-patch-anarci || python external/SNAC-DB/src/snacdb/patch.py
python "$OUT_DIR/scripts/download_snacdb_reference.py" "$OUT_DIR/reference/snacdb_curated" "$OUT_DIR/reference/REFERENCE_SOURCE.txt"

echo "[done] SNAC-DB setup complete. Activate with: conda activate $ENV_NAME"
