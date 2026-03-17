#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"

echo "[1/5] merge telemetry"
"$PYTHON_BIN" "$ROOT_DIR/scripts/01_merge_telemetry.py"

echo "[2/5] aggregate daily"
"$PYTHON_BIN" "$ROOT_DIR/scripts/02_aggregate_daily.py"

echo "[3/5] build facility features"
"$PYTHON_BIN" "$ROOT_DIR/scripts/03_build_facility_features.py"

echo "[4/5] build model panel"
"$PYTHON_BIN" "$ROOT_DIR/scripts/04_build_model_panel.py"

echo "[5/5] generate labels"
"$PYTHON_BIN" "$ROOT_DIR/scripts/05_generate_labels.py"

echo "Pipeline finished. Outputs in delivery_phase1/data/processed"
