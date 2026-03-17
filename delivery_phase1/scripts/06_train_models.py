from __future__ import annotations

from pathlib import Path
import json
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.impute import SimpleImputer
from sklearn.metrics import recall_score, roc_auc_score
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore", category=UserWarning)

try:
    from xgboost import XGBClassifier
except Exception:
    XGBClassifier = None

try:
    import shap
except Exception:
    shap = None

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "delivery_phase1"
DATA = BASE / "data" / "processed"
MODELS = BASE / "models"
REPORTS = BASE / "reports"
OUT = BASE / "output"
EXPL = OUT / "explanations"

for p in [MODELS, REPORTS, OUT, EXPL]:
    p.mkdir(parents=True, exist_ok=True)


def precision_at_k(y_true, y_prob, k_ratio=0.1):
    if len(y_true) == 0:
        return np.nan, 0
    k = max(1, int(len(y_true) * k_ratio))
    order = np.argsort(-y_prob)
    top = np.array(y_true)[order[:k]]
    return float(np.mean(top)), k


def time_split(df, train_ratio=0.7, val_ratio=0.15):
    n = len(df)
    t_end = int(n * train_ratio)
    v_end = int(n * (train_ratio + val_ratio))
    return df.iloc[:t_end], df.iloc[t_end:v_end], df.iloc[v_end:]


def robust_rank(series: pd.Series, invert: bool = False) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce")
    r = x.rank(pct=True).fillna(0.5)
    return 1 - r if invert else r


def metric_series(df: pd.DataFrame, primary: str, fallback: str | None = None) -> pd.Series:
    if primary in df.columns:
        return pd.to_numeric(df[primary], errors="coerce")
    if fallback and fallback in df.columns:
        return pd.to_numeric(df[fallback], errors="coerce")
    return pd.Series(np.full(len(df), np.nan), index=df.index)


def ensure_binary_from_score(score: pd.Series, q: float) -> pd.Series:
    s = pd.to_numeric(score, errors="coerce").fillna(score.median() if hasattr(score, "median") else 0)
    thr = s.quantile(q)
    y = (s >= thr).astype(int)
    # Keep training stable by forcing at least two classes.
    if y.nunique() < 2:
        y = (s >= s.median()).astype(int)
    return y


def add_multi_risk_labels(merged: pd.DataFrame) -> pd.DataFrame:
    out = merged.copy()

    rain = robust_rank(out.get("rainfall"))
    river = robust_rank(out.get("river_level"))
    gwl_stress = robust_rank(-pd.to_numeric(out.get("gwl"), errors="coerce"))
    near_river = robust_rank(out.get("dist_to_river_km"), invert=True)
    low_storage = robust_rank(1 - pd.to_numeric(out.get("storage_flag"), errors="coerce").fillna(1.0))
    crs = robust_rank(out.get("crs"))

    flood_score = (0.40 * rain + 0.35 * river + 0.20 * near_river + 0.05 * crs).clip(0, 1)
    water_shortage_score = (0.45 * gwl_stress + 0.20 * (1 - rain) + 0.20 * low_storage + 0.15 * crs).clip(0, 1)
    outage_score = (0.45 * rain + 0.30 * river + 0.10 * gwl_stress + 0.15 * crs).clip(0, 1)
    sanitation_score = (0.35 * flood_score + 0.30 * water_shortage_score + 0.20 * outage_score + 0.15 * low_storage).clip(0, 1)

    temp_raw = metric_series(out, "temperature", "temperature_value")
    humidity_raw = metric_series(out, "humidity", "humidity_value")
    temp = robust_rank(temp_raw)
    humidity = robust_rank(humidity_raw)
    heat_stress = (temp_raw > 40.0).astype(float)
    humid_heat = ((temp_raw > 38.0) & (humidity_raw > 65.0)).astype(float)

    # Human impact vulnerability proxy: schools (kids) and hospitals (elderly/patients) are more sensitive.
    fac_type = out.get("facility_type")
    if fac_type is not None:
        fac_type = fac_type.astype(str).str.lower()
        facility_sensitive = np.where(
            fac_type.eq("hospital") | fac_type.eq("school"),
            1.0,
            0.65,
        )
    else:
        facility_sensitive = np.full(len(out), 0.75)

    human_impact_score = (
        0.36 * temp
        + 0.26 * humidity
        + 0.14 * heat_stress
        + 0.14 * humid_heat
        + 0.10 * pd.Series(facility_sensitive, index=out.index)
    ).clip(0, 1)

    # 24h proxy labels.
    out["label_flood_24h"] = ensure_binary_from_score(flood_score, 0.80)
    out["label_water_shortage_24h"] = ensure_binary_from_score(water_shortage_score, 0.78)
    out["label_sanitation_failure_24h"] = ensure_binary_from_score(sanitation_score, 0.78)
    out["label_human_impact_24h"] = ensure_binary_from_score(human_impact_score, 0.78)

    # 7d proxy labels from short rolling persistence by facility.
    out = out.sort_values(["facility_id", "event_date"]).reset_index(drop=True)
    out["_flood_roll"] = out.groupby("facility_id")["label_flood_24h"].transform(lambda s: s.rolling(7, min_periods=1).mean())
    out["_water_roll"] = out.groupby("facility_id")["label_water_shortage_24h"].transform(lambda s: s.rolling(7, min_periods=1).mean())
    out["_san_roll"] = out.groupby("facility_id")["label_sanitation_failure_24h"].transform(lambda s: s.rolling(7, min_periods=1).mean())
    out["_human_roll"] = out.groupby("facility_id")["label_human_impact_24h"].transform(lambda s: s.rolling(7, min_periods=1).mean())

    out["label_flood_7d"] = ensure_binary_from_score(out["_flood_roll"], 0.75)
    out["label_water_shortage_7d"] = ensure_binary_from_score(out["_water_roll"], 0.75)
    out["label_sanitation_failure_7d"] = ensure_binary_from_score(out["_san_roll"], 0.75)
    out["label_human_impact_7d"] = ensure_binary_from_score(out["_human_roll"], 0.75)

    out = out.drop(columns=["_flood_roll", "_water_roll", "_san_roll", "_human_roll"])
    return out


def apply_weather_based_outage_7d_label(merged: pd.DataFrame) -> pd.DataFrame:
    out = merged.copy()

    rain_raw = metric_series(out, "rainfall", "rainfall_value")
    river_raw = metric_series(out, "river_level", "river_level_value")
    temp_raw = metric_series(out, "temperature", "temperature_value")
    humidity_raw = metric_series(out, "humidity", "humidity_value")
    wind_raw = metric_series(out, "wind_speed", "wind_speed_value")

    rain = robust_rank(rain_raw)
    river = robust_rank(river_raw)
    temp = robust_rank(temp_raw)
    humidity = robust_rank(humidity_raw)
    wind = robust_rank(wind_raw)
    near_river = robust_rank(out.get("dist_to_river_km"), invert=True)
    crs = robust_rank(out.get("crs"))

    heat_stress = (temp_raw > 40.0).astype(float)
    moisture_risk = (humidity_raw > 85.0).astype(float)
    storm_risk = ((rain_raw > 20.0) & (humidity_raw > 80.0)).astype(float)

    # Weather-directed logic: rainfall, wind, humidity, and temperature jointly drive outage persistence.
    weather_outage_score = (
        0.30 * rain
        + 0.18 * wind
        + 0.14 * humidity
        + 0.13 * temp
        + 0.12 * river
        + 0.08 * near_river
        + 0.05 * crs
        + 0.08 * heat_stress
        + 0.06 * moisture_risk
        + 0.06 * storm_risk
    ).clip(0, 1)

    observed = pd.to_numeric(out.get("label_outage_7d"), errors="coerce").fillna(0).astype(int)
    if observed.nunique() > 1:
        # Blend observed labels with weather stress so outage_7d remains data-grounded.
        blended = (0.65 * weather_outage_score + 0.35 * observed).clip(0, 1)
    else:
        blended = weather_outage_score

    out["label_outage_7d"] = ensure_binary_from_score(blended, 0.70)
    return out


def build_training_dataset(panel, labels, facility_features):
    date_df = panel.merge(labels, on="event_date", how="left")
    for c in ["label_outage_24h", "label_outage_7d"]:
        if c not in date_df.columns:
            date_df[c] = 0
        date_df[c] = pd.to_numeric(date_df[c], errors="coerce").fillna(0).astype(int)

    fac_cols = [
        c
        for c in [
            "facility_id",
            "facility_name",
            "facility_type",
            "district",
            "latitude",
            "longitude",
            "gwl_value",
            "rainfall_value",
            "river_level_value",
            "dist_to_river_km",
            "rolling_rain_3d",
            "river_anomaly",
            "storage_flag",
            "crs",
            "risk_level",
        ]
        if c in facility_features.columns
    ]
    fac = facility_features[fac_cols].copy()
    fac["_k"] = 1
    date_df["_k"] = 1
    merged = date_df.merge(fac, on="_k", how="inner").drop(columns=["_k"])

    temp_raw = metric_series(merged, "temperature", "temperature_value")
    humidity_raw = metric_series(merged, "humidity", "humidity_value")
    rain_raw = metric_series(merged, "rainfall", "rainfall_value")
    wind_raw = metric_series(merged, "wind_speed", "wind_speed_value")

    # Direct weather stress interaction features for ML.
    merged["heat_stress"] = (temp_raw > 40.0).astype(int)
    merged["moisture_risk"] = (humidity_raw > 85.0).astype(int)
    merged["storm_risk"] = ((rain_raw > 20.0) & (humidity_raw > 80.0)).astype(int)
    merged["weather_stress_index"] = (
        0.35 * robust_rank(rain_raw)
        + 0.25 * robust_rank(wind_raw)
        + 0.20 * robust_rank(humidity_raw)
        + 0.20 * robust_rank(temp_raw)
    ).clip(0, 1)
    merged["load_stress"] = temp_raw.fillna(temp_raw.median()) * (1.0 + robust_rank(merged.get("crs")))

    fallback_used = False
    if merged["label_outage_24h"].nunique() < 2 or merged["label_outage_7d"].nunique() < 2:
        fallback_used = True

        rain = metric_series(merged, "rainfall", "rainfall_value")
        rain = rain.fillna(rain.median())
        river = metric_series(merged, "river_level", "river_level_value")
        river = river.fillna(river.median())
        gwl = metric_series(merged, "gwl", "gwl_value")
        gwl = gwl.fillna(gwl.median())
        temp = metric_series(merged, "temperature", "temperature_value")
        temp = temp.fillna(temp.median())
        humidity = metric_series(merged, "humidity", "humidity_value")
        humidity = humidity.fillna(humidity.median())
        wind = metric_series(merged, "wind_speed", "wind_speed_value")
        wind = wind.fillna(wind.median())

        heat_stress = (temp > 40.0).astype(float)
        moisture_risk = (humidity > 85.0).astype(float)
        storm_risk = ((rain > 20.0) & (humidity > 80.0)).astype(float)

        stress = (
            rain.rank(pct=True).fillna(0) * 0.28
            + river.rank(pct=True).fillna(0) * 0.18
            + wind.rank(pct=True).fillna(0) * 0.17
            + humidity.rank(pct=True).fillna(0) * 0.14
            + temp.rank(pct=True).fillna(0) * 0.11
            + (-gwl).rank(pct=True).fillna(0) * 0.12
            + heat_stress * 0.05
            + moisture_risk * 0.05
            + storm_risk * 0.08
        )

        crs = pd.to_numeric(merged.get("crs"), errors="coerce").fillna(pd.to_numeric(merged.get("crs"), errors="coerce").median())
        dist = pd.to_numeric(merged.get("dist_to_river_km"), errors="coerce").fillna(pd.to_numeric(merged.get("dist_to_river_km"), errors="coerce").median())
        storage = pd.to_numeric(merged.get("storage_flag"), errors="coerce").fillna(1.0)

        vuln = (
            crs.rank(pct=True).fillna(0) * 0.50
            + (1 - dist.rank(pct=True).fillna(0)) * 0.30
            + (1 - storage.clip(0, 1)) * 0.20
        )

        risk = (0.70 * stress + 0.30 * vuln).clip(0, 1)
        merged["label_outage_24h"] = (risk >= risk.quantile(0.85)).astype(int)

        merged = merged.sort_values(["facility_id", "event_date"]).reset_index(drop=True)
        merged["risk_roll7"] = merged.groupby("facility_id")["label_outage_24h"].transform(lambda s: s.rolling(7, min_periods=1).mean())
        merged["label_outage_7d"] = (merged["risk_roll7"] >= merged["risk_roll7"].quantile(0.80)).astype(int)
        merged = merged.drop(columns=["risk_roll7"])

    # Rebuild outage_7d with weather-first logic for stronger weather-driven forecasting.
    merged = apply_weather_based_outage_7d_label(merged)

    # Always add multi-risk targets so we train model heads beyond outage-only.
    merged = add_multi_risk_labels(merged)

    return merged, fallback_used


def to_risk_label(v: pd.Series) -> pd.Series:
    return pd.cut(v, bins=[-np.inf, 0.33, 0.66, np.inf], labels=["Low", "Medium", "High"])


def build_models(pos_weight):
    models = {
        "rf": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=300,
                        max_depth=8,
                        min_samples_leaf=3,
                        class_weight="balanced",
                        random_state=42,
                        n_jobs=-1,
                    ),
                ),
            ]
        )
    }

    if XGBClassifier is not None:
        models["xgb"] = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    XGBClassifier(
                        n_estimators=300,
                        max_depth=5,
                        learning_rate=0.05,
                        subsample=0.9,
                        colsample_bytree=0.9,
                        reg_lambda=1.0,
                        eval_metric="logloss",
                        random_state=42,
                        n_jobs=4,
                        scale_pos_weight=max(1.0, float(pos_weight)),
                    ),
                ),
            ]
        )

    return models


def evaluate(y_true, y_prob):
    out = {}
    try:
        out["roc_auc"] = float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else np.nan
    except Exception:
        out["roc_auc"] = np.nan
    p_at_k, k = precision_at_k(y_true, y_prob, 0.1)
    out["precision_at_k"] = p_at_k
    out["k"] = k
    y_hat = (y_prob >= 0.5).astype(int)
    out["recall"] = float(recall_score(y_true, y_hat, zero_division=0))
    return out


def pick_best_threshold_for_f1(y_true, y_prob):
    y = np.array(y_true).astype(int)
    p = np.array(y_prob)

    if len(np.unique(y)) < 2:
        return 0.5

    candidates = np.linspace(0.10, 0.90, 81)
    best_t = 0.5
    best_f1 = -1.0
    for t in candidates:
        y_hat = (p >= t).astype(int)
        score = f1_score(y, y_hat, zero_division=0)
        if score > best_f1:
            best_f1 = score
            best_t = float(t)
    return best_t


def evaluate_with_threshold(y_true, y_prob, threshold):
    out = {}
    try:
        out["roc_auc"] = float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else np.nan
    except Exception:
        out["roc_auc"] = np.nan
    p_at_k, k = precision_at_k(y_true, y_prob, 0.1)
    out["precision_at_k"] = p_at_k
    out["k"] = k
    y_hat = (y_prob >= float(threshold)).astype(int)
    out["recall"] = float(recall_score(y_true, y_hat, zero_division=0))
    out["f1"] = float(f1_score(y_true, y_hat, zero_division=0))
    out["threshold"] = float(threshold)
    return out


def train_for_horizon(df, feature_cols, target_col, horizon_name):
    work = df.copy().sort_values("event_date").reset_index(drop=True)
    X = work[feature_cols]
    y = work[target_col].astype(int)

    train_df, val_df, test_df = time_split(work)
    X_train, y_train = train_df[feature_cols], train_df[target_col].astype(int)
    X_val, y_val = val_df[feature_cols], val_df[target_col].astype(int)
    X_test, y_test = test_df[feature_cols], test_df[target_col].astype(int)

    pos = max(1, int(y_train.sum()))
    neg = max(1, int((y_train == 0).sum()))
    pos_weight = neg / pos

    metrics_rows = []
    trained = {}

    for name, model in build_models(pos_weight).items():
        model.fit(X_train, y_train)
        p_val_raw = model.predict_proba(X_val)[:, 1]
        m_val = evaluate(y_val, p_val_raw)

        # Calibration with sigmoid and fold-based calibration over train+val.
        cal = CalibratedClassifierCV(model, method="sigmoid", cv=3)
        X_cal = pd.concat([X_train, X_val], axis=0)
        y_cal = pd.concat([y_train, y_val], axis=0)
        cal.fit(X_cal, y_cal)

        # Tune threshold on calibrated validation probabilities for better F1.
        p_val_cal = cal.predict_proba(X_val)[:, 1]
        tuned_threshold = pick_best_threshold_for_f1(y_val, p_val_cal)

        p_test = cal.predict_proba(X_test)[:, 1]
        m_test = evaluate_with_threshold(y_test, p_test, tuned_threshold)

        metrics_rows.append(
            {
                "horizon": horizon_name,
                "model": name,
                "val_roc_auc": m_val["roc_auc"],
                "test_roc_auc": m_test["roc_auc"],
                "test_precision_at_k": m_test["precision_at_k"],
                "test_recall": m_test["recall"],
                "test_f1": m_test["f1"],
                "decision_threshold": m_test["threshold"],
                "k": m_test["k"],
            }
        )
        trained[name] = {"base": model, "calibrated": cal, "metrics": m_test, "threshold": tuned_threshold}

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df = metrics_df.sort_values(["test_roc_auc", "test_precision_at_k"], ascending=False, na_position="last")
    best_name = metrics_df.iloc[0]["model"]
    best = trained[best_name]

    # Save models
    base_path = MODELS / f"{horizon_name}_{best_name}_base.joblib"
    cal_path = MODELS / f"{horizon_name}_{best_name}_calibrated.joblib"
    joblib.dump(best["base"], base_path)
    joblib.dump(best["calibrated"], cal_path)

    return {
        "metrics_df": metrics_df,
        "best_name": best_name,
        "best_base": best["base"],
        "best_cal": best["calibrated"],
        "best_threshold": best["threshold"],
        "test_df": test_df,
        "X_test": X_test,
        "y_test": y_test,
    }


def shap_top3_for_rows(base_model, X_rows, feature_names):
    if shap is None:
        return None

    # Extract underlying tree estimator from pipeline.
    est = base_model.named_steps.get("model", base_model)
    try:
        explainer = shap.TreeExplainer(est)
        values = explainer.shap_values(X_rows)
    except Exception:
        return None

    if isinstance(values, list):
        sv = values[1] if len(values) > 1 else values[0]
    else:
        sv = values

    sv = np.array(sv)
    if sv.ndim == 3:
        sv = sv[:, :, 1]

    rows = []
    for i in range(sv.shape[0]):
        vec = sv[i]
        order = np.argsort(-np.abs(vec))[:3]
        rows.append(
            {
                "row_index": i,
                "feature_1": feature_names[order[0]],
                "shap_1": float(vec[order[0]]),
                "feature_2": feature_names[order[1]] if len(order) > 1 else None,
                "shap_2": float(vec[order[1]]) if len(order) > 1 else np.nan,
                "feature_3": feature_names[order[2]] if len(order) > 2 else None,
                "shap_3": float(vec[order[2]]) if len(order) > 2 else np.nan,
            }
        )
    return pd.DataFrame(rows)


def build_facility_matrix(panel, facility_features, feature_cols):
    latest = panel.sort_values("event_date").iloc[-1]
    base_row = {c: latest.get(c, np.nan) for c in feature_cols}

    mapping = {
        "facility_gwl_value_mean": "gwl_value",
        "facility_rainfall_value_mean": "rainfall_value",
        "facility_river_level_value_mean": "river_level_value",
        "facility_dist_to_river_km_mean": "dist_to_river_km",
        "facility_rolling_rain_3d_mean": "rolling_rain_3d",
        "facility_river_anomaly_mean": "river_anomaly",
        "facility_storage_flag_mean": "storage_flag",
        "facility_crs_mean": "crs",
        "gwl_value": "gwl_value",
        "rainfall_value": "rainfall_value",
        "river_level_value": "river_level_value",
        "dist_to_river_km": "dist_to_river_km",
        "rolling_rain_3d": "rolling_rain_3d",
        "river_anomaly": "river_anomaly",
        "storage_flag": "storage_flag",
        "crs": "crs",
    }

    rows = []
    meta = []
    for r in facility_features.itertuples():
        row = dict(base_row)
        for dst, src in mapping.items():
            if dst in row and hasattr(r, src):
                row[dst] = getattr(r, src)
        rows.append(row)
        meta.append(
            {
                "facility_id": r.facility_id,
                "facility_name": r.facility_name,
                "facility_type": r.facility_type,
                "district": r.district,
                "latitude": getattr(r, "latitude", np.nan),
                "longitude": getattr(r, "longitude", np.nan),
                "crs": getattr(r, "crs", np.nan),
                "risk_level": getattr(r, "risk_level", None),
            }
        )

    return pd.DataFrame(rows), pd.DataFrame(meta)


def main():
    panel = pd.read_csv(DATA / "raipur_daily_model_features.csv")
    labels = pd.read_csv(DATA / "labels_raipur.csv")
    facility_features = pd.read_csv(DATA / "facility_features_raipur.csv")

    panel["event_date"] = pd.to_datetime(panel["event_date"], errors="coerce")
    labels["event_date"] = pd.to_datetime(labels["event_date"], errors="coerce")

    merged, fallback_used = build_training_dataset(panel, labels, facility_features)

    feature_cols = [
        c
        for c in merged.columns
        if c not in [
            "event_date",
            "label_outage_24h",
            "label_outage_7d",
            "label_flood_24h",
            "label_flood_7d",
            "label_water_shortage_24h",
            "label_water_shortage_7d",
            "label_sanitation_failure_24h",
            "label_sanitation_failure_7d",
            "label_human_impact_24h",
            "label_human_impact_7d",
            "outage_count",
            "facility_id",
            "facility_name",
            "facility_type",
            "district",
            "risk_level",
            "last_updated",
        ]
        and pd.api.types.is_numeric_dtype(merged[c])
    ]

    targets = {
        "outage": {"24h": "label_outage_24h", "7d": "label_outage_7d"},
        "flood": {"24h": "label_flood_24h", "7d": "label_flood_7d"},
        "water_shortage": {"24h": "label_water_shortage_24h", "7d": "label_water_shortage_7d"},
        "sanitation_failure": {"24h": "label_sanitation_failure_24h", "7d": "label_sanitation_failure_7d"},
        "human_impact": {"24h": "label_human_impact_24h", "7d": "label_human_impact_7d"},
    }

    trained = {}
    metrics_all = []
    for risk_name, hz_map in targets.items():
        trained[risk_name] = {}
        for hz, target_col in hz_map.items():
            run_name = f"{risk_name}_{hz}"
            t = train_for_horizon(merged, feature_cols, target_col, run_name)
            m = t["metrics_df"].copy()
            m["risk_type"] = risk_name
            m["horizon_bucket"] = hz
            metrics_all.append(m)
            trained[risk_name][hz] = t

    # Facility predictions from trained heads.
    X_fac, meta = build_facility_matrix(merged, facility_features, feature_cols)
    out24 = meta.copy()
    out7 = meta.copy()

    for risk_name in targets.keys():
        p24 = trained[risk_name]["24h"]["best_cal"].predict_proba(X_fac[feature_cols])[:, 1]
        p7 = trained[risk_name]["7d"]["best_cal"].predict_proba(X_fac[feature_cols])[:, 1]
        out24[f"pred_{risk_name}_prob_24h"] = p24
        out7[f"pred_{risk_name}_prob_7d"] = p7

    out24["priority_score_24h"] = (
        0.30 * out24["pred_outage_prob_24h"]
        + 0.175 * out24["pred_flood_prob_24h"]
        + 0.175 * out24["pred_water_shortage_prob_24h"]
        + 0.175 * out24["pred_sanitation_failure_prob_24h"]
        + 0.175 * out24["pred_human_impact_prob_24h"]
    ).clip(0, 1)
    out24["predicted_risk_label_24h"] = to_risk_label(out24["priority_score_24h"])
    out24 = out24.sort_values("priority_score_24h", ascending=False)

    out7["priority_score_7d"] = (
        0.30 * out7["pred_outage_prob_7d"]
        + 0.175 * out7["pred_flood_prob_7d"]
        + 0.175 * out7["pred_water_shortage_prob_7d"]
        + 0.175 * out7["pred_sanitation_failure_prob_7d"]
        + 0.175 * out7["pred_human_impact_prob_7d"]
    ).clip(0, 1)
    out7["predicted_risk_label_7d"] = to_risk_label(out7["priority_score_7d"])
    out7 = out7.sort_values("priority_score_7d", ascending=False)

    out24_path = OUT / "raipur_facility_outage_risk_24h.csv"
    out7_path = OUT / "raipur_facility_outage_risk_7d.csv"
    out24[[
        "facility_id",
        "facility_name",
        "facility_type",
        "district",
        "latitude",
        "longitude",
        "crs",
        "risk_level",
        "pred_outage_prob_24h",
        "pred_human_impact_prob_24h",
        "priority_score_24h",
        "predicted_risk_label_24h",
    ]].to_csv(out24_path, index=False)
    out7[[
        "facility_id",
        "facility_name",
        "facility_type",
        "district",
        "latitude",
        "longitude",
        "crs",
        "risk_level",
        "pred_outage_prob_7d",
        "pred_human_impact_prob_7d",
        "priority_score_7d",
        "predicted_risk_label_7d",
    ]].to_csv(out7_path, index=False)

    # Multi-risk decision-support output from trained model heads.
    multi = meta.copy()
    multi["flood_risk_prob"] = out24["pred_flood_prob_24h"].values
    multi["water_shortage_risk_prob"] = out24["pred_water_shortage_prob_24h"].values
    multi["power_outage_risk_prob"] = out24["pred_outage_prob_24h"].values
    multi["sanitation_failure_risk_prob"] = out24["pred_sanitation_failure_prob_24h"].values
    multi["human_impact_risk_prob"] = out24["pred_human_impact_prob_24h"].values

    multi["flood_risk_label"] = to_risk_label(multi["flood_risk_prob"])
    multi["water_shortage_risk_label"] = to_risk_label(multi["water_shortage_risk_prob"])
    multi["power_outage_risk_label"] = to_risk_label(multi["power_outage_risk_prob"])
    multi["sanitation_failure_risk_label"] = to_risk_label(multi["sanitation_failure_risk_prob"])
    multi["human_impact_risk_label"] = to_risk_label(multi["human_impact_risk_prob"])

    risk_cols = [
        "flood_risk_prob",
        "water_shortage_risk_prob",
        "power_outage_risk_prob",
        "sanitation_failure_risk_prob",
        "human_impact_risk_prob",
    ]
    arr = multi[risk_cols].to_numpy()
    i_max = arr.argmax(axis=1)
    multi["top_risk_type"] = [risk_cols[i].replace("_risk_prob", "") for i in i_max]
    multi["top_risk_score"] = arr.max(axis=1)

    high_any = (multi[risk_cols] >= 0.70).any(axis=1)
    med_count = (multi[risk_cols] >= 0.60).sum(axis=1)
    multi["alert_flag"] = np.where(high_any | (med_count >= 2), True, False)
    multi["alert_level"] = np.where(multi["top_risk_score"] >= 0.80, "Critical", np.where(multi["alert_flag"], "High", "Normal"))

    out_multi = OUT / "raipur_facility_multi_risk.csv"
    out_alerts = OUT / "raipur_alerts_multi_risk_high.csv"
    multi = multi.sort_values(["alert_flag", "top_risk_score"], ascending=[False, False]).reset_index(drop=True)
    multi.to_csv(out_multi, index=False)
    multi[multi["alert_flag"]].to_csv(out_alerts, index=False)

    # SHAP top features per facility for each risk head/horizon.
    for risk_name in targets.keys():
        for hz in ["24h", "7d"]:
            shp = shap_top3_for_rows(trained[risk_name][hz]["best_base"], X_fac[feature_cols], feature_cols)
            if shp is None:
                continue
            ex = meta[["facility_id", "facility_name"]].reset_index(drop=True).join(shp)
            ex["risk_type"] = risk_name
            ex["horizon"] = hz
            ex.to_csv(EXPL / f"top3_features_{risk_name}_{hz}.csv", index=False)

    # Backward-compatible outage explanation files.
    if (EXPL / "top3_features_outage_24h.csv").exists():
        pd.read_csv(EXPL / "top3_features_outage_24h.csv").to_csv(EXPL / "top3_features_24h.csv", index=False)
    if (EXPL / "top3_features_outage_7d.csv").exists():
        pd.read_csv(EXPL / "top3_features_outage_7d.csv").to_csv(EXPL / "top3_features_7d.csv", index=False)

    # Combined top-10 examples.
    top10 = multi.head(10).merge(
        (pd.read_csv(EXPL / "top3_features_24h.csv") if (EXPL / "top3_features_24h.csv").exists() else pd.DataFrame()),
        on=["facility_id", "facility_name"],
        how="left",
    )
    top10.to_csv(EXPL / "top10_facilities_with_explanations.csv", index=False)

    # Metrics report.
    metrics = pd.concat(metrics_all, ignore_index=True)
    metrics_csv = REPORTS / "model_metrics_table.csv"
    metrics.to_csv(metrics_csv, index=False)

    def metrics_markdown(df: pd.DataFrame) -> str:
        cols = list(df.columns)
        header = "| " + " | ".join(cols) + " |\n"
        sep = "|" + "|".join(["---"] * len(cols)) + "|\n"
        rows = []
        for _, r in df.iterrows():
            vals = []
            for c in cols:
                v = r[c]
                if isinstance(v, float):
                    vals.append(f"{v:.6f}" if not np.isnan(v) else "nan")
                else:
                    vals.append(str(v))
            rows.append("| " + " | ".join(vals) + " |\n")
        return header + sep + "".join(rows)

    report = REPORTS / "model_eval.md"
    lines = []
    lines.append("# Model Evaluation (Task E)\n\n")
    lines.append("## Data and Labeling\n")
    lines.append(f"- Training rows: {len(merged)}\n")
    lines.append(f"- Feature columns: {len(feature_cols)}\n")
    lines.append(f"- Fallback labels used: {'Yes' if fallback_used else 'No'}\n")
    if fallback_used:
        lines.append("- Fallback strategy: climate-stress percentile proxy generated from rainfall, wind speed, humidity, temperature, river level, and groundwater when outage labels were single-class.\n")
    lines.append("\n## Metrics\n")
    lines.append(metrics_markdown(metrics))
    lines.append("\n\n## Selected Models\n")
    for risk_name in targets.keys():
        lines.append(f"- {risk_name} 24h best model: {trained[risk_name]['24h']['best_name']} (calibrated)\n")
        lines.append(f"- {risk_name} 7d best model: {trained[risk_name]['7d']['best_name']} (calibrated)\n")
    lines.append("\n## Output Artifacts\n")
    lines.append(f"- Facility risk 24h: {out24_path}\n")
    lines.append(f"- Facility risk 7d: {out7_path}\n")
    lines.append(f"- Multi-risk table: {out_multi}\n")
    lines.append(f"- Alerts table: {out_alerts}\n")
    lines.append(f"- Explanations dir: {EXPL}\n")
    lines.append(f"- Models dir: {MODELS}\n")

    report.write_text("".join(lines), encoding="utf-8")

    manifest = {
        "fallback_labels_used": fallback_used,
        "best_models": {
            risk_name: {
                "24h": trained[risk_name]["24h"]["best_name"],
                "7d": trained[risk_name]["7d"]["best_name"],
            }
            for risk_name in targets.keys()
        },
        "outputs": {
            "risk_24h": str(out24_path),
            "risk_7d": str(out7_path),
            "multi_risk": str(out_multi),
            "alerts": str(out_alerts),
            "metrics_table": str(metrics_csv),
            "model_eval": str(report),
            "explanations": str(EXPL),
        },
    }
    (REPORTS / "task_e_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("Task E completed")
    print(f"Fallback labels used: {fallback_used}")
    for risk_name in targets.keys():
        print(f"{risk_name} 24h best: {trained[risk_name]['24h']['best_name']}")
        print(f"{risk_name} 7d best: {trained[risk_name]['7d']['best_name']}")
    print(f"Saved: {out24_path}")
    print(f"Saved: {out7_path}")
    print(f"Saved: {out_multi}")
    print(f"Saved: {out_alerts}")
    print(f"Saved: {report}")


if __name__ == "__main__":
    main()
