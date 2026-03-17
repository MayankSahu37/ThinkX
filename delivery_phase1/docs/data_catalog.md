# ThinkX Data Catalog (Phase 1)

Generated from workspace data files in an isolated delivery folder.

## Canonical Facility Master Recommendation
- Recommended canonical master: `export.csv` (has stable IDs + richer address fields including full/street).
- Reconciliation steps if both are present:
  - Normalize key: map `export.csv.@id` -> `facility_id`.
  - Prefer `facility_name/facility_type` from generated master where curated, but retain addresses from `export.csv`.
  - Keep unmatched IDs in `reports/reconciliation_facility_crs.csv` in Task B.

## Catalog Table

| filename | type (raw/processed) | producer/script | primary keys | date range | brief usage/downstream notes | sample first-row preview |
|---|---|---|---|---|---|---|
| all_outages_today.csv | raw | ThinkX.ipynb (Cell 2) | tbd | 2026-03-14 00:00:00 to 2026-03-14 00:00:00 | Used in ETL/model/dashboard chain. | {"SN": "1", "Name of Town": "", "Maintenance activity Scheduled for": "11KV KONI", "Outage Affected Area": "MASTURI DC", "Outage Area": "BREAKDOWN", "Outage Start Date": "2026-0... |
| all_outages_tomorrow.csv | raw | ThinkX.ipynb (Cell 2) | tbd | n/a | Used in ETL/model/dashboard chain. | {"0": "Filter By:-", "1": "Town:", "2": "--Select--", "3": "Scheduled for:", "4": "--Select--", "5": "", "Outage_Type": "All Outages (Tomorrow)"} |
| combined_outages.csv | raw | ThinkX.ipynb (Cell 1/2) | SN, Outage Start Date, Outage Start Time (approx) | 2026-03-14 00:00:00 to 2026-03-14 00:00:00 | Used in ETL/model/dashboard chain. | {"SN": "1.0", "Name of Town": "DURG", "Maintenance activity Scheduled for": "11KV PUSHP VATIKA", "Outage Affected Area": "BAGHERA", "Outage Area": "...", "Outage Start Date": "2... |
| export.csv | raw | Input master (OSM export) | @id | n/a | Canonical master candidate for facilities and addresses; join on @id/facility_id. | {"X": "81.6232005", "Y": "21.2414376", "id": "node/3774564938", "@id": "node/3774564938", "addr:city": "Raipur", "addr:district": "", "addr:full": "", "addr:housenumber": "", "a... |
| GWL_2021-2025_Telementry_Hourly.xlsx | raw | unknown | tbd | n/a | Excel source file used for telemetry ingestion. | (binary/xlsx) |
| GWL_2026-2030_Telementry_Hourly.csv | raw | one_zero.ipynb / raw download | tbd | n/a | Used in ETL/model/dashboard chain. | (empty) |
| live_outages.csv | raw | ThinkX.ipynb (Cell 2) | tbd | 2026-03-14 00:00:00 to 2026-03-14 00:00:00 | Used in ETL/model/dashboard chain. | {"SN": "1", "Name of Town": "DURG", "Maintenance activity Scheduled for": "11KV PUSHP VATIKA", "Outage Affected Area": "BAGHERA", "Outage Area": "...", "Outage Start Date": "202... |
| processed_outputs/crs_predictions_raipur_facilities.csv | processed | ThinkX.ipynb (Cell 11 enrichment) | facility_id | 2026-03-14 02:31:00 to 2026-03-14 02:31:00 | Facility-level CRS + enriched addresses for area-to-facility linkage. | {"facility_id": "node/6956627669", "facility_name": "Raipur Institute Of Medical Sciences Hospital", "facility_type": "Hospital", "district": "RAIPUR", "crs": "0.375", "risk_lev... |
| processed_outputs/environmental_daily_raipur.csv | processed | ProcessedFile.ipynb | metric, date | 2022-01-04 00:00:00 to 2026-03-03 00:00:00 | Used in ETL/model/dashboard chain. | {"metric": "gwl", "date": "2022-09-07", "mean_value": "-5.7895", "min_value": "-6.807", "max_value": "-4.772", "records": "2"} |
| processed_outputs/environmental_long_raipur.csv | processed | ProcessedFile.ipynb | metric, station, timestamp | 2022-01-04 00:00:00 to 2026-03-03 05:00:00 | Used in ETL/model/dashboard chain. | {"metric": "gwl", "station": "Mandir Hasoud", "district": "RAIPUR", "state": "Chhattisgarh", "latitude": "21.22472222", "longitude": "81.76694444", "timestamp": "2022-09-07 12:4... |
| processed_outputs/facilities_master_generated_raipur.csv | processed | ProcessedFile.ipynb | facility_id | n/a | Used in ETL/model/dashboard chain. | {"facility_id": "node/3774564938", "facility_name": "bagri nursing home", "facility_type": "Hospital", "district": "RAIPUR", "latitude": "21.2414376", "longitude": "81.6232005"} |
| processed_outputs/facility_crs_raipur.csv | processed | ProcessedFile.ipynb | facility_id | 2026-03-14 02:31:42 to 2026-03-14 02:31:42 | CRS input feature for modeling; do not recompute unless reconciliation requested. | {"facility_id": "node/6956627669", "facility_name": "Raipur Institute Of Medical Sciences Hospital", "facility_type": "Hospital", "district": "RAIPUR", "crs": "0.375", "risk_lev... |
| processed_outputs/facility_features_raipur.csv | processed | ProcessedFile.ipynb | facility_id | 2026-03-14 02:31:42 to 2026-03-14 02:31:42 | Used in ETL/model/dashboard chain. | {"facility_id": "node/3774564938", "facility_name": "bagri nursing home", "facility_type": "Hospital", "district": "RAIPUR", "latitude": "21.2414376", "longitude": "81.6232005",... |
| processed_outputs/imd_snapshot_20260313_214127.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/imd_snapshot_20260313_214831.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/imd_snapshot_20260313_215255.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/imd_snapshot_20260313_220351.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/imd_snapshot_20260313_220412.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/openweather_snapshot_20260313_214127.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/openweather_snapshot_20260313_214831.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/openweather_snapshot_20260313_215255.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/openweather_snapshot_20260313_220351.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/openweather_snapshot_20260313_220412.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/openweather_snapshot_20260313_222354.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/raipur_daily_model_features.csv | processed | ThinkX.ipynb (Cell 10) | event_date | 2022-01-04 00:00:00 to 2026-03-02 00:00:00 | Model panel for 24h/7d outage model training. | {"event_date": "2022-01-04", "climate_gwl": "0.0", "climate_rainfall": "11.8", "climate_river_level": "314.65635849056605", "outage_events": "0.0", "hospital_events": "0.0", "sc... |
| processed_outputs/raipur_facility_outage_risk_24h.csv | processed | ThinkX.ipynb (Cell 10) | facility_id | n/a | Dashboard/API priority ranking output. | {"facility_id": "node/4445117924", "facility_name": "Krishna Public School", "facility_type": "School", "district": "RAIPUR", "latitude": "21.1943876", "longitude": "81.6635818"... |
| processed_outputs/weather_snapshot_20260313_214127.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/weather_snapshot_20260313_214831.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/weather_snapshot_20260313_215255.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/weather_snapshot_20260313_220351.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/weather_snapshot_20260313_220412.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/weather_snapshot_20260313_222354.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/weatherstack_snapshot_20260313_215255.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/weatherstack_snapshot_20260313_220351.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/weatherstack_snapshot_20260313_220412.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| processed_outputs/weatherstack_snapshot_20260313_222354.json | processed | processed_outputs/weather_realtime.py | n/a | timestamp in filename | Weather/provider snapshot for deterministic replay and debugging. | (json object) |
| rainfall_2021_2025_2026-03-13.csv | raw | one_zero.ipynb | tbd | 2022-01-03 00:00:00 to 2025-12-12 18:00:00 | Used in ETL/model/dashboard chain. | {"SlNo": "1", "Station": "Agar_Mungeli", "Agency": "Chhattisgarh SW", "State LGD Code": "22", "State": "Chhattisgarh", "District LGD Code": "375", "District": "BILASPUR", "Tehsi... |
| rainfall_2026_2030_2026-03-13.csv | raw | one_zero.ipynb | tbd | 2026-01-01 05:00:00 to 2026-12-01 14:00:00 | Used in ETL/model/dashboard chain. | {"SlNo": "1", "Station": "Agar_Mungeli", "Agency": "Chhattisgarh SW", "State LGD Code": "22", "State": "Chhattisgarh", "District LGD Code": "375", "District": "BILASPUR", "Tehsi... |
| Riverwater_level_2021_2025_raipur.csv | raw | one_zero.ipynb | tbd | 2022-01-04 15:13:00 to 2025-12-12 23:00:00 | Used in ETL/model/dashboard chain. | {"_id": "80190", "SlNo": "80190", "Station": "Ballar", "Agency": "Chhattisgarh SW", "State LGD Code": "22", "State": "Chhattisgarh", "District LGD Code": "387", "District": "RAI... |
| riverwater_level_2026_2030_raipur.csv | raw | one_zero.ipynb | tbd | 2026-01-01 00:00:00 to 2026-12-02 23:00:00 | Used in ETL/model/dashboard chain. | {"SlNo": "3441", "Station": "Ballar", "Agency": "Chhattisgarh SW", "State LGD Code": "22", "State": "Chhattisgarh", "District LGD Code": "387", "District": "RAIPUR", "Tehsil": "... |

## Sample Heads

First 10 rows are written to `docs/data_samples/head_<filename>.csv` for major CSVs.
