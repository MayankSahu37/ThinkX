# Model Evaluation (Task E)

## Data and Labeling
- Training rows: 219336
- Feature columns: 31
- Fallback labels used: Yes
- Fallback strategy: climate-stress percentile proxy generated from rainfall, wind speed, humidity, temperature, river level, and groundwater when outage labels were single-class.

## Metrics
| horizon | model | val_roc_auc | test_roc_auc | test_precision_at_k | test_recall | test_f1 | decision_threshold | k | risk_type | horizon_bucket |
|---|---|---|---|---|---|---|---|---|---|---|
| outage_24h | xgb | 0.983784 | 0.991780 | 1.000000 | 0.827866 | 0.897861 | 0.480000 | 3290 | outage | 24h |
| outage_24h | rf | 0.955372 | 0.981184 | 0.992097 | 0.497973 | 0.660098 | 0.460000 | 3290 | outage | 24h |
| outage_7d | rf | 0.795614 | 0.743255 | 0.907295 | 0.406873 | 0.541528 | 0.470000 | 3290 | outage | 7d |
| outage_7d | xgb | 0.821380 | 0.723191 | 0.924620 | 0.507249 | 0.586615 | 0.410000 | 3290 | outage | 7d |
| flood_24h | xgb | 0.998549 | 0.997917 | 1.000000 | 0.960556 | 0.972856 | 0.530000 | 3290 | flood | 24h |
| flood_24h | rf | 0.984374 | 0.977635 | 1.000000 | 0.802384 | 0.882108 | 0.580000 | 3290 | flood | 24h |
| flood_7d | rf | 0.778818 | 0.880612 | 0.998784 | 0.699295 | 0.801627 | 0.350000 | 3290 | flood | 7d |
| flood_7d | xgb | 0.703654 | 0.854330 | 0.998784 | 0.646631 | 0.757586 | 0.370000 | 3290 | flood | 7d |
| water_shortage_24h | xgb | 0.994899 | 1.000000 | 0.745897 | 1.000000 | 1.000000 | 0.360000 | 3290 | water_shortage | 24h |
| water_shortage_24h | rf | 0.988595 | 0.999878 | 0.745897 | 1.000000 | 0.993321 | 0.390000 | 3290 | water_shortage | 24h |
| water_shortage_7d | xgb | 0.517669 | 0.838400 | 0.632827 | 0.539658 | 0.548689 | 0.380000 | 3290 | water_shortage | 7d |
| water_shortage_7d | rf | 0.521068 | 0.836819 | 0.549848 | 0.399689 | 0.488516 | 0.270000 | 3290 | water_shortage | 7d |
| sanitation_failure_24h | xgb | 0.995592 | 0.994037 | 1.000000 | 0.931538 | 0.951594 | 0.570000 | 3290 | sanitation_failure | 24h |
| sanitation_failure_24h | rf | 0.977071 | 0.964812 | 0.998176 | 0.701150 | 0.810284 | 0.580000 | 3290 | sanitation_failure | 24h |
| sanitation_failure_7d | rf | 0.747868 | 0.844075 | 0.996049 | 0.452017 | 0.610973 | 0.310000 | 3290 | sanitation_failure | 7d |
| sanitation_failure_7d | xgb | 0.729242 | 0.799050 | 0.906383 | 0.387875 | 0.534905 | 0.300000 | 3290 | sanitation_failure | 7d |
| human_impact_24h | rf | 0.999909 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.280000 | 3290 | human_impact | 24h |
| human_impact_24h | xgb | 0.999911 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.180000 | 3290 | human_impact | 24h |
| human_impact_7d | xgb | 0.779747 | 0.453349 | 0.134954 | 1.000000 | 0.298503 | 0.100000 | 3290 | human_impact | 7d |
| human_impact_7d | rf | 0.805332 | 0.394298 | 0.181763 | 1.000000 | 0.298503 | 0.100000 | 3290 | human_impact | 7d |


## Selected Models
- outage 24h best model: xgb (calibrated)
- outage 7d best model: rf (calibrated)
- flood 24h best model: xgb (calibrated)
- flood 7d best model: rf (calibrated)
- water_shortage 24h best model: xgb (calibrated)
- water_shortage 7d best model: xgb (calibrated)
- sanitation_failure 24h best model: xgb (calibrated)
- sanitation_failure 7d best model: rf (calibrated)
- human_impact 24h best model: rf (calibrated)
- human_impact 7d best model: xgb (calibrated)

## Output Artifacts
- Facility risk 24h: C:\Users\ASUS\Downloads\ThinkX_database\delivery_phase1\output\raipur_facility_outage_risk_24h.csv
- Facility risk 7d: C:\Users\ASUS\Downloads\ThinkX_database\delivery_phase1\output\raipur_facility_outage_risk_7d.csv
- Multi-risk table: C:\Users\ASUS\Downloads\ThinkX_database\delivery_phase1\output\raipur_facility_multi_risk.csv
- Alerts table: C:\Users\ASUS\Downloads\ThinkX_database\delivery_phase1\output\raipur_alerts_multi_risk_high.csv
- Explanations dir: C:\Users\ASUS\Downloads\ThinkX_database\delivery_phase1\output\explanations
- Models dir: C:\Users\ASUS\Downloads\ThinkX_database\delivery_phase1\models
