from __future__ import annotations

import pandas as pd

from _common import (
    ROOT,
    PROCESSED_DIR,
    find_col,
    file_priority,
    norm_cols,
    parse_ts_series,
    safe_read_csv,
    safe_read_xlsx,
)


def load_metric(files, metric_name, value_col_opts, allowed_district_tokens=None):
    frames = []
    for f in files:
        if not f.exists():
            continue
        df = safe_read_csv(f) if f.suffix.lower() == ".csv" else safe_read_xlsx(f)
        if df.empty:
            continue
        df = norm_cols(df)

        station_col = find_col(df.columns, ["station"])
        district_col = find_col(df.columns, ["district"])
        state_col = find_col(df.columns, ["state"])

        # Prefer textual district/state names over LGD code columns.
        if district_col and "lgd" in district_col.lower():
            district_name_cols = [c for c in df.columns if "district" in str(c).lower() and "lgd" not in str(c).lower()]
            if district_name_cols:
                district_col = district_name_cols[0]
        if state_col and "lgd" in state_col.lower():
            state_name_cols = [c for c in df.columns if "state" in str(c).lower() and "lgd" not in str(c).lower()]
            if state_name_cols:
                state_col = state_name_cols[0]
        lat_col = find_col(df.columns, ["latitude", "lat"])
        lon_col = find_col(df.columns, ["longitude", "lon"])
        ts_col = find_col(df.columns, ["data acquisition time", "timestamp", "date"])

        val_col = None
        for opt in value_col_opts:
            val_col = find_col(df.columns, [opt])
            if val_col:
                break

        if not (station_col and ts_col and val_col):
            continue

        out = pd.DataFrame(
            {
                "metric": metric_name,
                "station": df[station_col].astype(str).str.strip(),
                "district": df[district_col].astype(str).str.strip() if district_col else "",
                "state": df[state_col].astype(str).str.strip() if state_col else "",
                "latitude": pd.to_numeric(df[lat_col], errors="coerce") if lat_col else pd.NA,
                "longitude": pd.to_numeric(df[lon_col], errors="coerce") if lon_col else pd.NA,
                "timestamp": parse_ts_series(df[ts_col]),
                "value": pd.to_numeric(df[val_col], errors="coerce"),
                "source_file": f.name,
                "_priority": file_priority(f.name),
            }
        )

        # Restrict to selected districts where district exists.
        if out["district"].astype(str).str.strip().ne("").any():
            if allowed_district_tokens is None:
                out = out[out["district"].astype(str).str.upper().str.contains("RAIPUR", na=False)]
            else:
                mask = pd.Series(False, index=out.index)
                for token in allowed_district_tokens:
                    mask = mask | out["district"].astype(str).str.upper().str.contains(str(token).upper(), na=False)
                out = out[mask]

        frames.append(out)

    if not frames:
        return pd.DataFrame(columns=["metric", "station", "district", "state", "latitude", "longitude", "timestamp", "value", "source_file"])

    all_df = pd.concat(frames, ignore_index=True)
    all_df = all_df.dropna(subset=["station", "timestamp", "value"])
    # Overlap dedupe: prefer row from file with later range/date priority.
    all_df = all_df.sort_values(["metric", "station", "timestamp", "_priority"]).drop_duplicates(["metric", "station", "timestamp"], keep="last")
    all_df = all_df.drop(columns=["_priority"])
    return all_df


def load_humidity_nasa_monthly(path):
    if not path.exists():
        return pd.DataFrame(columns=["metric", "station", "district", "state", "latitude", "longitude", "timestamp", "value", "source_file"])

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return pd.DataFrame(columns=["metric", "station", "district", "state", "latitude", "longitude", "timestamp", "value", "source_file"])

    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().upper().startswith("PARAMETER,YEAR"):
            header_idx = i
            break
    if header_idx is None:
        return pd.DataFrame(columns=["metric", "station", "district", "state", "latitude", "longitude", "timestamp", "value", "source_file"])

    try:
        df = pd.read_csv(path, skiprows=header_idx)
    except Exception:
        return pd.DataFrame(columns=["metric", "station", "district", "state", "latitude", "longitude", "timestamp", "value", "source_file"])

    df = norm_cols(df)
    if "YEAR" not in df.columns:
        return pd.DataFrame(columns=["metric", "station", "district", "state", "latitude", "longitude", "timestamp", "value", "source_file"])

    month_cols = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    present_months = [c for c in month_cols if c in df.columns]
    if not present_months:
        return pd.DataFrame(columns=["metric", "station", "district", "state", "latitude", "longitude", "timestamp", "value", "source_file"])

    work = df.copy()
    work["YEAR"] = pd.to_numeric(work["YEAR"], errors="coerce")
    work = work.dropna(subset=["YEAR"])
    if work.empty:
        return pd.DataFrame(columns=["metric", "station", "district", "state", "latitude", "longitude", "timestamp", "value", "source_file"])

    long_df = work.melt(id_vars=["YEAR"], value_vars=present_months, var_name="month", value_name="value")
    month_map = {m: i + 1 for i, m in enumerate(month_cols)}
    long_df["month_num"] = long_df["month"].map(month_map)
    long_df["value"] = pd.to_numeric(long_df["value"], errors="coerce")
    long_df = long_df.dropna(subset=["month_num", "value"])

    long_df["timestamp"] = pd.to_datetime(
        {
            "year": long_df["YEAR"].astype(int),
            "month": long_df["month_num"].astype(int),
            "day": 1,
        },
        errors="coerce",
    )
    long_df = long_df.dropna(subset=["timestamp"])
    long_df["timestamp"] = long_df["timestamp"].dt.tz_localize("Asia/Kolkata")

    return pd.DataFrame(
        {
            "metric": "humidity",
            "station": "Raipur_NASA_POWER",
            "district": "RAIPUR",
            "state": "Chhattisgarh",
            "latitude": 21.2415,
            "longitude": 81.6676,
            "timestamp": long_df["timestamp"],
            "value": long_df["value"],
            "source_file": path.name,
        }
    )


def main():
    rain_files = [
        ROOT / "rainfall_2021_2025_2026-03-13.csv",
        ROOT / "rainfall_2026_2030_2026-03-13.csv",
    ]
    river_files = [
        ROOT / "Riverwater_level_2021_2025_raipur.csv",
        ROOT / "riverwater_level_2026_2030_raipur.csv",
    ]
    gwl_files = [
        ROOT / "GWL_2021-2025_Telementry_Hourly.xlsx",
        ROOT / "GWL_2026-2030_Telementry_Hourly.csv",
    ]
    temperature_files = [
        ROOT / "temprature_tel_hr_chhattisgarh_sw_cg_2021_2025.csv",
        ROOT / "temprature_tel_hr_chhattisgarh_sw_cg_2026_2030.csv",
    ]
    humidity_files = [
        ROOT / "Humidity_2020-2025_data.csv",
    ]
    wind_files = [
        ROOT / "windSpeed_BSP_2022-2025.csv",
    ]

    rain = load_metric(rain_files, "rainfall", ["telemetry hourly rainfall", "rainfall"])
    river = load_metric(river_files, "river_level", ["river water level telemetry hourly", "river water level"])
    gwl = load_metric(gwl_files, "gwl", ["groundwater level telemetry 6 hourly", "groundwater level"])
    temperature = load_metric(
        temperature_files,
        "temperature",
        ["air temperature telemetry hourly", "temperature", "air temperature"],
        allowed_district_tokens=["RAIPUR", "BILASPUR"],
    )
    humidity = load_humidity_nasa_monthly(humidity_files[0]) if humidity_files else pd.DataFrame()
    # Use Bilaspur nearest-district wind telemetry as Raipur proxy when Raipur wind stations are unavailable.
    wind = load_metric(
        wind_files,
        "wind_speed",
        ["telemetry hourly wind speed", "wind speed"],
        allowed_district_tokens=["RAIPUR", "BILASPUR"],
    )
    if not wind.empty:
        wind["district"] = "RAIPUR"
        wind["station"] = wind["station"].astype(str).str.strip() + " (BILASPUR_PROXY)"
        wind["source_file"] = wind["source_file"].astype(str) + " [bilaspur_proxy_for_raipur]"

    if not temperature.empty:
        temp_raipur = temperature[temperature["district"].astype(str).str.upper().str.contains("RAIPUR", na=False)]
        if temp_raipur.empty:
            temperature["district"] = "RAIPUR"
            temperature["station"] = temperature["station"].astype(str).str.strip() + " (BILASPUR_PROXY)"
            temperature["source_file"] = temperature["source_file"].astype(str) + " [bilaspur_proxy_for_raipur]"

    env_long = pd.concat([rain, river, gwl, temperature, humidity, wind], ignore_index=True)

    if env_long.empty:
        # Fallback to existing processed telemetry for reproducibility.
        prev = norm_cols(safe_read_csv(ROOT / "processed_outputs" / "environmental_long_raipur.csv"))
        if not prev.empty:
            ts_col = find_col(prev.columns, ["timestamp", "time", "date"])
            metric_col = find_col(prev.columns, ["metric"])
            station_col = find_col(prev.columns, ["station"])
            district_col = find_col(prev.columns, ["district"])
            state_col = find_col(prev.columns, ["state"])
            lat_col = find_col(prev.columns, ["latitude", "lat"])
            lon_col = find_col(prev.columns, ["longitude", "lon"])
            value_col = find_col(prev.columns, ["value", "mean_value"])
            src_col = find_col(prev.columns, ["source"])
            if ts_col and metric_col and station_col and value_col:
                env_long = pd.DataFrame(
                    {
                        "metric": prev[metric_col].astype(str),
                        "station": prev[station_col].astype(str),
                        "district": prev[district_col].astype(str) if district_col else "",
                        "state": prev[state_col].astype(str) if state_col else "",
                        "latitude": pd.to_numeric(prev[lat_col], errors="coerce") if lat_col else pd.NA,
                        "longitude": pd.to_numeric(prev[lon_col], errors="coerce") if lon_col else pd.NA,
                        "timestamp": parse_ts_series(prev[ts_col]),
                        "value": pd.to_numeric(prev[value_col], errors="coerce"),
                        "source_file": prev[src_col].astype(str) if src_col else "processed_outputs/environmental_long_raipur.csv",
                    }
                )

    env_long = env_long.dropna(subset=["metric", "station", "timestamp", "value"])
    env_long = env_long.sort_values(["metric", "station", "timestamp"]).drop_duplicates(["metric", "station", "timestamp"])

    # Backfill missing weather metrics from previously generated processed output.
    required_metrics = {"rainfall", "river_level", "gwl", "temperature", "humidity", "wind_speed"}
    present_metrics = set(env_long["metric"].astype(str).unique()) if not env_long.empty else set()
    missing_metrics = sorted(required_metrics - present_metrics)
    if missing_metrics:
        prev = norm_cols(safe_read_csv(ROOT / "processed_outputs" / "environmental_long_raipur.csv"))
        if not prev.empty:
            ts_col = find_col(prev.columns, ["timestamp", "time", "date"])
            metric_col = find_col(prev.columns, ["metric"])
            station_col = find_col(prev.columns, ["station"])
            district_col = find_col(prev.columns, ["district"])
            state_col = find_col(prev.columns, ["state"])
            lat_col = find_col(prev.columns, ["latitude", "lat"])
            lon_col = find_col(prev.columns, ["longitude", "lon"])
            value_col = find_col(prev.columns, ["value", "mean_value"])
            src_col = find_col(prev.columns, ["source"])
            if ts_col and metric_col and station_col and value_col:
                prev_df = pd.DataFrame(
                    {
                        "metric": prev[metric_col].astype(str),
                        "station": prev[station_col].astype(str),
                        "district": prev[district_col].astype(str) if district_col else "",
                        "state": prev[state_col].astype(str) if state_col else "",
                        "latitude": pd.to_numeric(prev[lat_col], errors="coerce") if lat_col else pd.NA,
                        "longitude": pd.to_numeric(prev[lon_col], errors="coerce") if lon_col else pd.NA,
                        "timestamp": parse_ts_series(prev[ts_col]),
                        "value": pd.to_numeric(prev[value_col], errors="coerce"),
                        "source_file": prev[src_col].astype(str) if src_col else "processed_outputs/environmental_long_raipur.csv",
                    }
                )
                prev_df = prev_df[prev_df["metric"].astype(str).isin(missing_metrics)]
                if not prev_df.empty:
                    env_long = pd.concat([env_long, prev_df], ignore_index=True)
                    env_long = env_long.dropna(subset=["metric", "station", "timestamp", "value"])
                    env_long = env_long.sort_values(["metric", "station", "timestamp"]).drop_duplicates(
                        ["metric", "station", "timestamp"], keep="last"
                    )

    # Simple unit check: convert rainfall to mm if values look like meters.
    rain_max = env_long.loc[env_long["metric"] == "rainfall", "value"].max() if not env_long.empty else None
    if pd.notna(rain_max) and rain_max < 2:
        env_long.loc[env_long["metric"] == "rainfall", "value"] *= 1000

    out = PROCESSED_DIR / "environmental_long_raipur.csv"
    env_long.to_csv(out, index=False)
    print(f"Wrote: {out} ({len(env_long)} rows)")


if __name__ == "__main__":
    main()
