# Task C Pipeline (Reproducible ETL)

This folder contains a reproducible ETL chain for Raipur prototype outputs.

## Run

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\delivery_phase1\run_pipeline.ps1
```

POSIX shell:

```bash
PYTHON_BIN=python ./delivery_phase1/run_pipeline.sh
```

If using the local virtual environment explicitly:

```bash
PYTHON_BIN="c:/Users/ASUS/Downloads/ThinkX_database/.venv/Scripts/python.exe" ./delivery_phase1/run_pipeline.sh
```

## Scripts

1. `scripts/01_merge_telemetry.py`
- Merges rainfall/river/gwl split-range files.
- Dedupe key: `(metric, station, timestamp)`.
- Overlap rule: prefer later file priority derived from filename range/date.
- Output: `data/processed/environmental_long_raipur.csv`.

2. `scripts/02_aggregate_daily.py`
- Builds daily telemetry aggregates by metric/date.
- Output: `data/processed/environmental_daily_raipur.csv`.

3. `scripts/03_build_facility_features.py`
- Builds canonical Raipur facilities master.
- Computes facility features including `rolling_rain_3d`, `river_anomaly`, `dist_to_river_km`, `storage_flag`.
- Uses `facility_crs_raipur.csv` only as input feature source.
- Outputs: `data/processed/facilities_master_raipur.csv`, `data/processed/facility_features_raipur.csv`.

4. `scripts/04_build_model_panel.py`
- Creates daily model panel with environmental + facility aggregate features + mean CRS input column.
- Output: `data/processed/raipur_daily_model_features.csv`.

5. `scripts/05_generate_labels.py`
- Builds 24h/7d labels from outage datasets for Raipur.
- Output: `data/processed/labels_raipur.csv`.

## Generated Files

- `delivery_phase1/data/processed/environmental_long_raipur.csv`
- `delivery_phase1/data/processed/environmental_daily_raipur.csv`
- `delivery_phase1/data/processed/facilities_master_raipur.csv`
- `delivery_phase1/data/processed/facility_features_raipur.csv`
- `delivery_phase1/data/processed/raipur_daily_model_features.csv`
- `delivery_phase1/data/processed/labels_raipur.csv`
