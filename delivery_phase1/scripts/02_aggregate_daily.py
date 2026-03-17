from __future__ import annotations

import pandas as pd

from _common import PROCESSED_DIR, TZ_NAME, find_col, norm_cols, parse_ts_series, safe_read_csv


def main():
    src = PROCESSED_DIR / "environmental_long_raipur.csv"
    df = norm_cols(safe_read_csv(src))
    if df.empty:
        raise RuntimeError(f"Missing or empty source: {src}")

    ts_col = find_col(df.columns, ["timestamp", "time", "date"])
    metric_col = find_col(df.columns, ["metric"])
    value_col = find_col(df.columns, ["value"])
    if not (ts_col and metric_col and value_col):
        raise RuntimeError("environmental_long_raipur.csv missing required columns")

    df["timestamp"] = parse_ts_series(df[ts_col])
    df = df.dropna(subset=["timestamp"])
    df["date"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True).dt.tz_convert(TZ_NAME).dt.date
    df["value"] = pd.to_numeric(df[value_col], errors="coerce")
    df = df.dropna(subset=["value", "date"])

    daily = (
        df.groupby([metric_col, "date"], as_index=False)
        .agg(mean_value=("value", "mean"), min_value=("value", "min"), max_value=("value", "max"), records=("value", "size"))
        .rename(columns={metric_col: "metric"})
        .sort_values(["metric", "date"])
    )

    out = PROCESSED_DIR / "environmental_daily_raipur.csv"
    daily.to_csv(out, index=False)
    print(f"Wrote: {out} ({len(daily)} rows)")


if __name__ == "__main__":
    main()
