from __future__ import annotations

import pandas as pd

from _common import PROCESSED_DIR, ROOT, norm_cols, safe_read_csv


def main():
    daily = norm_cols(safe_read_csv(PROCESSED_DIR / "environmental_daily_raipur.csv"))
    features = norm_cols(safe_read_csv(PROCESSED_DIR / "facility_features_raipur.csv"))
    crs = norm_cols(safe_read_csv(ROOT / "processed_outputs" / "facility_crs_raipur.csv"))

    if daily.empty or features.empty:
        raise RuntimeError("Missing required sources for model panel")

    daily["date"] = pd.to_datetime(daily["date"], errors="coerce")
    piv = (
        daily.pivot_table(index="date", columns="metric", values="mean_value", aggfunc="mean")
        .reset_index()
        .rename(columns={"date": "event_date"})
    )

    # Facility aggregate feature block (constant across dates; suitable baseline for panel-level model).
    agg_cols = [
        c
        for c in [
            "gwl_value",
            "rainfall_value",
            "river_level_value",
            "dist_to_river_km",
            "rolling_rain_3d",
            "river_anomaly",
            "storage_flag",
            "crs",
        ]
        if c in features.columns
    ]
    agg_vals = features[agg_cols].mean(numeric_only=True).to_dict()
    for k, v in agg_vals.items():
        piv[f"facility_{k}_mean"] = v

    # Carry CRS as explicit input feature from canonical CRS source.
    if not crs.empty and "crs" in crs.columns:
        piv["facility_crs_mean"] = pd.to_numeric(crs["crs"], errors="coerce").mean()
    else:
        piv["facility_crs_mean"] = pd.to_numeric(features.get("crs"), errors="coerce").mean()

    piv["dow"] = piv["event_date"].dt.dayofweek
    piv["month"] = piv["event_date"].dt.month

    out = PROCESSED_DIR / "raipur_daily_model_features.csv"
    piv.to_csv(out, index=False)
    print(f"Wrote: {out} ({len(piv)} rows)")


if __name__ == "__main__":
    main()
