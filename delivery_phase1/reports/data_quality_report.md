# Data Quality Report (Task B)
## Scope
- Cleaned outputs written under `delivery_phase1/data/clean/`.
- Canonical facility master derived from `export.csv` (Raipur hospitals/schools only).
- Timezone mapping: ambiguous naive timestamps localized to `Asia/Kolkata` (UTC+05:30).

## Telemetry Merge & Dedupe Rules
- Split-range files merged by `(metric, station, timestamp)`.
- On overlap, kept the row from file with later filename-derived priority (later range/date).
- Dedupe key for telemetry: `(metric, station, timestamp)`.

## Units Check
- No unit conversion applied; source units appear consistent (rainfall=mm, river/gwl=m).

## environmental_long_raipur.csv
- Rows: 222983
- Unparsable timestamps: 0
- Missingness matrix (% missing):

| column | missing_pct |
|---|---:|
| metric | 0.0 |
| station | 0.0 |
| district | 0.0 |
| state | 0.0 |
| latitude | 0.0 |
| longitude | 0.0 |
| timestamp | 0.0 |
| value | 0.0 |
| source_file | 0.0 |

## environmental_daily_raipur.csv
- Rows: 2955
- Missingness matrix (% missing):

| column | missing_pct |
|---|---:|
| metric | 0.0 |
| date | 0.0 |
| mean_value | 0.0 |
| min_value | 0.0 |
| max_value | 0.0 |
| records | 0.0 |

## facilities_master_raipur.csv
- Rows: 148
- Missingness matrix (% missing):

| column | missing_pct |
|---|---:|
| facility_id | 0.0 |
| facility_name | 0.0 |
| latitude | 0.0 |
| longitude | 0.0 |
| facility_type | 0.0 |
| district | 0.0 |
| street_address | 0.0 |
| complete_address | 0.0 |

## facility_features_raipur.csv
- Rows: 148
- Missingness matrix (% missing):

| column | missing_pct |
|---|---:|
| facility_id | 0.0 |
| facility_name | 0.0 |
| facility_type | 0.0 |
| district | 0.0 |
| latitude | 0.0 |
| longitude | 0.0 |
| gwl_value | 0.0 |
| rainfall_value | 0.0 |
| river_level_value | 0.0 |
| outage_risk | 0.0 |
| water_availability | 0.0 |
| flood_safety | 0.0 |
| rainfall_stability | 0.0 |
| electricity_reliability | 0.0 |
| crs | 0.0 |
| risk_level | 0.0 |
| last_updated | 0.0 |

## facility_crs_raipur.csv
- Rows: 148
- Missingness matrix (% missing):

| column | missing_pct |
|---|---:|
| facility_id | 0.0 |
| facility_name | 0.0 |
| facility_type | 0.0 |
| district | 0.0 |
| crs | 0.0 |
| risk_level | 0.0 |
| last_updated | 0.0 |

## Station/Gauge Mapping Sanity
- Distance threshold: 25.0 km
- Gauges with lat/lon: 23
- Facilities mapped to nearest gauge within threshold: 147/148
- Median nearest-gauge distance (km): 2.52

## CRS Reconciliation
- Reconciliation file: `delivery_phase1/reports/reconciliation_facility_crs.csv`
- Matched keys: 148
- Mismatches: 0
