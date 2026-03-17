from __future__ import annotations

import numpy as np
import pandas as pd

from _common import (
    PROCESSED_DIR,
    ROOT,
    ensure_facility_master,
    haversine_km,
    norm_cols,
    parse_ts_series,
    safe_read_csv,
)


def nearest_distance_km(lat, lon, gauges_df):
    if gauges_df.empty:
        return np.nan
    dists = [haversine_km(lat, lon, float(r.latitude), float(r.longitude)) for r in gauges_df.itertuples()]
    return float(min(dists)) if dists else np.nan


def main():
    fac_path = ensure_facility_master()
    facilities = norm_cols(safe_read_csv(fac_path))

    env_long = norm_cols(safe_read_csv(PROCESSED_DIR / "environmental_long_raipur.csv"))
    env_daily = norm_cols(safe_read_csv(PROCESSED_DIR / "environmental_daily_raipur.csv"))
    crs = norm_cols(safe_read_csv(ROOT / "processed_outputs" / "facility_crs_raipur.csv"))

    if facilities.empty or env_long.empty or env_daily.empty:
        raise RuntimeError("Required sources missing for facility feature build")

    env_long["timestamp"] = parse_ts_series(env_long["timestamp"])
    env_long = env_long.dropna(subset=["timestamp", "value", "latitude", "longitude"])
    env_long["value"] = pd.to_numeric(env_long["value"], errors="coerce")
    env_long = env_long.dropna(subset=["value"])

    latest = (
        env_long.sort_values(["metric", "station", "timestamp"]).groupby(["metric", "station"], as_index=False).tail(1)
    )

    river_gauges = latest[latest["metric"] == "river_level"][ ["station", "latitude", "longitude", "value"] ].copy()
    gauges_all = latest[["metric", "station", "latitude", "longitude", "value"]].copy()

    rows = []
    for r in facilities.itertuples():
        lat = float(r.latitude)
        lon = float(r.longitude)

        # nearest-by-metric values
        vals = {}
        for metric in ["gwl", "rainfall", "river_level", "temperature", "humidity", "wind_speed"]:
            g = gauges_all[gauges_all["metric"] == metric]
            if g.empty:
                vals[metric] = np.nan
                continue
            d = g.apply(lambda x: haversine_km(lat, lon, float(x["latitude"]), float(x["longitude"])), axis=1)
            idx = d.idxmin()
            vals[metric] = float(g.loc[idx, "value"])

        dist_to_river = nearest_distance_km(lat, lon, river_gauges)

        rows.append(
            {
                "facility_id": r.facility_id,
                "facility_name": r.facility_name,
                "facility_type": r.facility_type,
                "district": r.district,
                "latitude": lat,
                "longitude": lon,
                "gwl_value": vals.get("gwl"),
                "rainfall_value": vals.get("rainfall"),
                "river_level_value": vals.get("river_level"),
                "temperature_value": vals.get("temperature"),
                "humidity_value": vals.get("humidity"),
                "wind_speed_value": vals.get("wind_speed"),
                "dist_to_river_km": dist_to_river,
            }
        )

    feat = pd.DataFrame(rows)

    # Rolling rain and river anomaly from daily table.
    daily = env_daily.copy()
    daily["date"] = pd.to_datetime(daily["date"], errors="coerce")

    rain_daily = daily[daily["metric"] == "rainfall"].sort_values("date")
    river_daily = daily[daily["metric"] == "river_level"].sort_values("date")

    rain_roll3 = float(rain_daily["mean_value"].tail(3).mean()) if not rain_daily.empty else np.nan
    river_now = float(river_daily["mean_value"].iloc[-1]) if not river_daily.empty else np.nan
    river_ref = float(river_daily["mean_value"].tail(30).mean()) if not river_daily.empty else np.nan
    river_anom = river_now - river_ref if pd.notna(river_now) and pd.notna(river_ref) else np.nan

    feat["rolling_rain_3d"] = rain_roll3
    feat["river_anomaly"] = river_anom

    # Weather stress features for outage prediction.
    feat["heat_stress"] = (pd.to_numeric(feat["temperature_value"], errors="coerce") > 40.0).astype(int)
    feat["moisture_risk"] = (pd.to_numeric(feat["humidity_value"], errors="coerce") > 85.0).astype(int)
    feat["storm_risk"] = (
        (pd.to_numeric(feat["rainfall_value"], errors="coerce") > 20.0)
        & (pd.to_numeric(feat["humidity_value"], errors="coerce") > 80.0)
    ).astype(int)

    # Heuristic storage flag for simulation readiness.
    feat["storage_flag"] = np.where(
        (feat["facility_type"].astype(str).str.lower() == "hospital") | (feat["gwl_value"].fillna(-999) > -8),
        1,
        0,
    )

    # Carry CRS as feature (input only).
    if not crs.empty and "facility_id" in crs.columns:
        keep = [c for c in ["facility_id", "crs", "risk_level", "last_updated"] if c in crs.columns]
        feat = feat.merge(crs[keep].drop_duplicates(subset=["facility_id"]), on="facility_id", how="left")

    # Demand/load proxy: temperature stress scaled by facility risk sensitivity.
    crs_norm = pd.to_numeric(feat.get("crs"), errors="coerce")
    if crs_norm.notna().any():
        cmin = crs_norm.min()
        cmax = crs_norm.max()
        if pd.notna(cmin) and pd.notna(cmax) and cmax != cmin:
            crs_norm = (crs_norm - cmin) / (cmax - cmin)
        else:
            crs_norm = pd.Series(np.full(len(feat), 0.5), index=feat.index)
    else:
        crs_norm = pd.Series(np.full(len(feat), 0.5), index=feat.index)
    feat["load_stress"] = pd.to_numeric(feat.get("temperature_value"), errors="coerce").fillna(0) * (1.0 + crs_norm.fillna(0.5))

    # Derived helper columns for downstream parity.
    feat["water_availability"] = feat["gwl_value"].fillna(feat["gwl_value"].median())
    feat["flood_safety"] = -feat["river_level_value"].fillna(feat["river_level_value"].median())
    feat["rainfall_stability"] = -abs(feat["river_anomaly"].fillna(0))
    feat["electricity_reliability"] = feat["storage_flag"].astype(float)

    out_feat = PROCESSED_DIR / "facility_features_raipur.csv"
    feat.to_csv(out_feat, index=False)
    print(f"Wrote: {out_feat} ({len(feat)} rows)")


if __name__ == "__main__":
    main()
