from __future__ import annotations

from pathlib import Path
import glob
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "delivery_phase1"
DATA = BASE / "data" / "processed"
OUT = BASE / "output"
REPORTS = BASE / "reports"

for p in [OUT, REPORTS]:
    p.mkdir(parents=True, exist_ok=True)


def norm01(s: pd.Series, invert: bool = False) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    vmin = x.min()
    vmax = x.max()
    if pd.isna(vmin) or pd.isna(vmax) or vmax == vmin:
        z = pd.Series(np.full(len(x), 0.5), index=x.index)
    else:
        z = (x - vmin) / (vmax - vmin)
    z = z.clip(0, 1)
    return 1 - z if invert else z


def risk_label(v: pd.Series) -> pd.Series:
    return pd.cut(v, bins=[-np.inf, 0.33, 0.66, np.inf], labels=["Low", "Medium", "High"])


def load_latest_weather_context() -> dict:
    paths = sorted(glob.glob(str(ROOT / "processed_outputs" / "weather_snapshot_*.json")))
    if not paths:
        return {
            "pop_next24_max": 0.0,
            "rain_next24_mm": 0.0,
            "temp_current_c": np.nan,
            "humidity_current": np.nan,
            "source_file": None,
        }

    latest = paths[-1]
    try:
        with open(latest, "r", encoding="utf-8") as f:
            j = json.load(f)
    except Exception:
        return {
            "pop_next24_max": 0.0,
            "rain_next24_mm": 0.0,
            "temp_current_c": np.nan,
            "humidity_current": np.nan,
            "source_file": latest,
        }

    active = j.get("weather_active", {})
    current_payload = (((active.get("current_weather") or {}).get("payload")) or {})
    temp = ((current_payload.get("main") or {}).get("temp"))
    humidity = ((current_payload.get("main") or {}).get("humidity"))

    fc = (((active.get("forecast_5d_raw") or {}).get("payload") or {}).get("list")) or []
    fc24 = fc[:8] if isinstance(fc, list) else []  # 3-hourly x 8 = next 24h
    pop_vals = [float(item.get("pop", 0) or 0) for item in fc24]
    rain_vals = [float(((item.get("rain") or {}).get("3h", 0) or 0)) for item in fc24]

    return {
        "pop_next24_max": max(pop_vals) if pop_vals else 0.0,
        "rain_next24_mm": float(sum(rain_vals)) if rain_vals else 0.0,
        "temp_current_c": float(temp) if temp is not None else np.nan,
        "humidity_current": float(humidity) if humidity is not None else np.nan,
        "source_file": latest,
    }


def main():
    p24 = pd.read_csv(OUT / "raipur_facility_outage_risk_24h.csv")
    p7 = pd.read_csv(OUT / "raipur_facility_outage_risk_7d.csv")
    feat = pd.read_csv(DATA / "facility_features_raipur.csv")

    keep_cols = [
        "facility_id",
        "facility_name",
        "facility_type",
        "district",
        "latitude",
        "longitude",
        "crs",
        "risk_level",
        "gwl_value",
        "rainfall_value",
        "river_level_value",
        "dist_to_river_km",
        "storage_flag",
    ]
    keep_cols = [c for c in keep_cols if c in feat.columns]

    df = p24.merge(
        p7[["facility_id", "pred_outage_prob_7d"]],
        on="facility_id",
        how="left",
    ).merge(
        feat[keep_cols],
        on="facility_id",
        how="left",
        suffixes=("", "_feat"),
    )

    weather_ctx = load_latest_weather_context()

    # Facility-level normalized components
    n_river = norm01(df.get("river_level_value"))
    n_rain = norm01(df.get("rainfall_value"))
    n_gwl_stress = norm01(-pd.to_numeric(df.get("gwl_value"), errors="coerce"))
    n_near_river = norm01(df.get("dist_to_river_km"), invert=True)
    n_out24 = norm01(df.get("pred_outage_prob_24h"))
    n_out7 = norm01(df.get("pred_outage_prob_7d"))
    n_crs = norm01(df.get("crs"))
    n_storage_fail = norm01(1 - pd.to_numeric(df.get("storage_flag"), errors="coerce").fillna(1))

    # Weather context modifiers (same city-wide, still useful for scenario shifting)
    pop24 = float(weather_ctx["pop_next24_max"])
    rain24 = float(weather_ctx["rain_next24_mm"])
    temp_c = weather_ctx["temp_current_c"]

    rain24_norm = 0.0 if rain24 <= 0 else min(1.0, rain24 / 80.0)
    temp_norm = 0.5 if pd.isna(temp_c) else max(0.0, min(1.0, (temp_c - 20.0) / 20.0))

    # Risk heads
    df["flood_risk_prob"] = (
        0.40 * n_river
        + 0.25 * n_near_river
        + 0.20 * n_rain
        + 0.15 * n_out24
        + 0.10 * pop24
        + 0.10 * rain24_norm
    ).clip(0, 1)

    df["water_shortage_risk_prob"] = (
        0.35 * n_gwl_stress
        + 0.25 * temp_norm
        + 0.15 * n_storage_fail
        + 0.15 * n_out24
        + 0.10 * (1 - n_rain)
    ).clip(0, 1)

    df["power_outage_risk_prob"] = (
        0.65 * pd.to_numeric(df["pred_outage_prob_24h"], errors="coerce").fillna(0)
        + 0.25 * pd.to_numeric(df["pred_outage_prob_7d"], errors="coerce").fillna(0)
        + 0.10 * n_crs
    ).clip(0, 1)

    df["sanitation_failure_risk_prob"] = (
        0.35 * df["flood_risk_prob"]
        + 0.35 * df["water_shortage_risk_prob"]
        + 0.20 * df["power_outage_risk_prob"]
        + 0.10 * n_storage_fail
    ).clip(0, 1)

    # Labels
    df["flood_risk_label"] = risk_label(df["flood_risk_prob"])
    df["water_shortage_risk_label"] = risk_label(df["water_shortage_risk_prob"])
    df["power_outage_risk_label"] = risk_label(df["power_outage_risk_prob"])
    df["sanitation_failure_risk_label"] = risk_label(df["sanitation_failure_risk_prob"])

    risk_cols = [
        "flood_risk_prob",
        "water_shortage_risk_prob",
        "power_outage_risk_prob",
        "sanitation_failure_risk_prob",
    ]

    arr = df[risk_cols].to_numpy()
    i_max = arr.argmax(axis=1)
    df["top_risk_type"] = [risk_cols[i].replace("_risk_prob", "") for i in i_max]
    df["top_risk_score"] = arr.max(axis=1)

    # Alert logic
    high_any = (df[risk_cols] >= 0.70).any(axis=1)
    med_count = (df[risk_cols] >= 0.60).sum(axis=1)
    df["alert_flag"] = np.where(high_any | (med_count >= 2), True, False)
    df["alert_level"] = np.where(df["top_risk_score"] >= 0.80, "Critical", np.where(df["alert_flag"], "High", "Normal"))

    df["weather_context_pop_next24_max"] = pop24
    df["weather_context_rain_next24_mm"] = rain24
    df["weather_context_temp_current_c"] = temp_c
    df["weather_context_source_file"] = weather_ctx.get("source_file")

    # Final ordering
    out_cols = [
        "facility_id",
        "facility_name",
        "facility_type",
        "district",
        "latitude",
        "longitude",
        "crs",
        "pred_outage_prob_24h",
        "pred_outage_prob_7d",
        "flood_risk_prob",
        "flood_risk_label",
        "water_shortage_risk_prob",
        "water_shortage_risk_label",
        "power_outage_risk_prob",
        "power_outage_risk_label",
        "sanitation_failure_risk_prob",
        "sanitation_failure_risk_label",
        "top_risk_type",
        "top_risk_score",
        "alert_flag",
        "alert_level",
        "weather_context_pop_next24_max",
        "weather_context_rain_next24_mm",
        "weather_context_temp_current_c",
        "weather_context_source_file",
    ]
    out_cols = [c for c in out_cols if c in df.columns]

    multi = df[out_cols].sort_values(["alert_flag", "top_risk_score"], ascending=[False, False]).reset_index(drop=True)

    out_multi = OUT / "raipur_facility_multi_risk.csv"
    out_alerts = OUT / "raipur_alerts_multi_risk_high.csv"
    out_report = REPORTS / "multi_risk_summary.md"

    multi.to_csv(out_multi, index=False)
    multi[multi["alert_flag"]].to_csv(out_alerts, index=False)

    label_counts = {
        "flood": multi["flood_risk_label"].value_counts(dropna=False).to_dict(),
        "water_shortage": multi["water_shortage_risk_label"].value_counts(dropna=False).to_dict(),
        "power_outage": multi["power_outage_risk_label"].value_counts(dropna=False).to_dict(),
        "sanitation_failure": multi["sanitation_failure_risk_label"].value_counts(dropna=False).to_dict(),
    }

    lines = []
    lines.append("# Multi-Risk Prediction Summary\n\n")
    lines.append("This report extends the model output from outage-only prediction to multi-risk scoring.\n\n")
    lines.append("## Risk Heads\n")
    lines.append("- Flood risk\n")
    lines.append("- Water shortage risk\n")
    lines.append("- Power outage risk\n")
    lines.append("- Sanitation failure risk\n\n")
    lines.append("## Label Distribution\n")
    for k, v in label_counts.items():
        lines.append(f"- {k}: {v}\n")
    lines.append("\n")
    lines.append(f"- Total facilities scored: {len(multi)}\n")
    lines.append(f"- Alerted facilities: {int(multi['alert_flag'].sum())}\n")
    lines.append(f"- Weather context source: {weather_ctx.get('source_file')}\n")
    lines.append(f"- Weather POP next 24h max: {pop24}\n")
    lines.append(f"- Weather rain next 24h total (mm): {rain24}\n")
    lines.append("\n## Output Files\n")
    lines.append(f"- {out_multi}\n")
    lines.append(f"- {out_alerts}\n")

    out_report.write_text("".join(lines), encoding="utf-8")

    print("Multi-risk prediction completed")
    print(f"Saved: {out_multi}")
    print(f"Saved: {out_alerts}")
    print(f"Saved: {out_report}")
    print(f"Facilities scored: {len(multi)}")
    print(f"Alerts: {int(multi['alert_flag'].sum())}")


if __name__ == "__main__":
    main()
