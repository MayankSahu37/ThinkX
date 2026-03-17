from __future__ import annotations

import pandas as pd

from _common import PROCESSED_DIR, ROOT, find_col, norm_cols, parse_ts_series, safe_read_csv


def main():
    combined = norm_cols(safe_read_csv(ROOT / "combined_outages.csv"))
    live = norm_cols(safe_read_csv(ROOT / "live_outages.csv"))
    panel = norm_cols(safe_read_csv(PROCESSED_DIR / "raipur_daily_model_features.csv"))

    if panel.empty:
        raise RuntimeError("Model panel missing, run step 04 first")

    raw = pd.concat([combined, live], ignore_index=True)
    if raw.empty:
        labels = panel[["event_date"]].copy()
        labels["label_outage_24h"] = 0
        labels["label_outage_7d"] = 0
        out = PROCESSED_DIR / "labels_raipur.csv"
        labels.to_csv(out, index=False)
        print(f"Wrote: {out} ({len(labels)} rows; no outage source)")
        return

    c_town = find_col(raw.columns, ["name of town", "town", "city", "district"])
    c_area = find_col(raw.columns, ["outage area", "affected area", "area"])
    c_date = find_col(raw.columns, ["outage start date", "start date", "date"])
    c_time = find_col(raw.columns, ["outage start time", "start time", "time"])

    if not c_date:
        raise RuntimeError("Outage source missing start date column")

    text = pd.Series("", index=raw.index)
    if c_town:
        text = text + " " + raw[c_town].astype(str)
    if c_area:
        text = text + " " + raw[c_area].astype(str)
    raw = raw[text.str.contains("raipur", case=False, na=False)].copy()

    if c_time:
        raw["event_ts"] = parse_ts_series(raw[c_date].astype(str) + " " + raw[c_time].astype(str))
    else:
        raw["event_ts"] = parse_ts_series(raw[c_date])

    raw = raw.dropna(subset=["event_ts"])
    raw["event_date"] = pd.to_datetime(raw["event_ts"], errors="coerce", utc=True).dt.tz_convert("Asia/Kolkata").dt.floor("D").dt.tz_localize(None)

    daily_count = raw.groupby("event_date", as_index=False).size().rename(columns={"size": "outage_count"})

    panel["event_date"] = pd.to_datetime(panel["event_date"], errors="coerce")
    labels = panel[["event_date"]].merge(daily_count, on="event_date", how="left")
    labels["outage_count"] = labels["outage_count"].fillna(0)

    labels = labels.sort_values("event_date")
    labels["label_outage_24h"] = (labels["outage_count"].shift(-1).fillna(0) > 0).astype(int)
    labels["label_outage_7d"] = (
        labels["outage_count"].shift(-1).rolling(7, min_periods=1).sum().fillna(0) > 0
    ).astype(int)

    out = PROCESSED_DIR / "labels_raipur.csv"
    labels.to_csv(out, index=False)
    print(f"Wrote: {out} ({len(labels)} rows)")


if __name__ == "__main__":
    main()
