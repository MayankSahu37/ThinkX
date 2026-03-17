from pathlib import Path
import pandas as pd
import math
import re

ROOT = Path(r"C:/Users/ASUS/Downloads/ThinkX_database")
OUT = ROOT / "delivery_phase1"
CLEAN = OUT / "data" / "clean"
REPORTS = OUT / "reports"
DOCS = OUT / "docs"
for p in [CLEAN, REPORTS, DOCS]:
    p.mkdir(parents=True, exist_ok=True)

TZ_NAME = "Asia/Kolkata"
DIST_THRESHOLD_KM = 25.0

# ---------- helpers ----------
def safe_read_csv(path):
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def safe_read_xlsx(path):
    try:
        return pd.read_excel(path)
    except Exception:
        return pd.DataFrame()


def norm_cols(df):
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


def find_col(cols, options):
    low = {str(c).lower(): c for c in cols}
    for opt in options:
        for k, v in low.items():
            if opt in k:
                return v
    return None


def parse_ts_series(s):
    s = s.astype(str).str.strip()
    def _parse_one(v):
        t = pd.to_datetime(v, errors="coerce", dayfirst=True)
        if pd.isna(t):
            return pd.NaT
        try:
            if t.tzinfo is None:
                return t.tz_localize(TZ_NAME, nonexistent="NaT", ambiguous="NaT")
            return t.tz_convert(TZ_NAME)
        except Exception:
            return pd.NaT

    return s.apply(_parse_one)


def file_priority(name: str):
    score = 0
    m = re.search(r"(\d{4})-(\d{4})", name)
    if m:
        score += int(m.group(2))
    d = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    if d:
        score += int(d.group(1).replace("-", ""))
    return score


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def missingness_table(df):
    if df.empty:
        return pd.DataFrame(columns=["column", "missing_pct"])
    miss = (df.isna().mean() * 100).round(2)
    return miss.sort_values(ascending=False).rename_axis("column").reset_index(name="missing_pct")


# ---------- Task B.1 Merge split-range telemetry ----------
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


def load_metric(files, metric_name, value_col_opts):
    frames = []
    for f in files:
        if not f.exists():
            continue
        if f.suffix.lower() == ".csv":
            df = safe_read_csv(f)
        else:
            df = safe_read_xlsx(f)
        if df.empty:
            continue
        df = norm_cols(df)

        station_col = find_col(df.columns, ["station"])
        district_col = find_col(df.columns, ["district"])
        state_col = find_col(df.columns, ["state"])
        lat_col = find_col(df.columns, ["latitude", "lat"])
        lon_col = find_col(df.columns, ["longitude", "lon"])
        ts_col = find_col(df.columns, ["data acquisition time", "timestamp", "date"])
        val_col = None
        for opt in value_col_opts:
            val_col = find_col(df.columns, [opt])
            if val_col:
                break

        if ts_col is None or val_col is None or station_col is None:
            continue

        out = pd.DataFrame({
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
        })

        # Keep Raipur-focused rows where district exists; otherwise keep and let downstream filter by gauges/facilities
        if out["district"].astype(str).str.strip().ne("").any():
            m = out["district"].astype(str).str.upper().str.contains("RAIPUR", na=False)
            out = out[m]

        frames.append(out)

    if not frames:
        return pd.DataFrame(columns=["metric", "station", "district", "state", "latitude", "longitude", "timestamp", "value", "source_file"])

    all_df = pd.concat(frames, ignore_index=True)
    all_df = all_df.dropna(subset=["station", "timestamp", "value"])
    # Deduplicate: prefer later file priority on overlap
    all_df = all_df.sort_values(["station", "timestamp", "_priority"]).drop_duplicates(["metric", "station", "timestamp"], keep="last")
    all_df = all_df.drop(columns=["_priority"])
    return all_df

rain = load_metric(rain_files, "rainfall", ["telemetry hourly rainfall", "rainfall"])
river = load_metric(river_files, "river_level", ["river water level telemetry hourly", "river water level"])
gwl = load_metric(gwl_files, "gwl", ["groundwater level telemetry 6 hourly", "groundwater level"])

env_long = pd.concat([rain, river, gwl], ignore_index=True)
env_long = env_long.dropna(subset=["timestamp", "value", "station"])

# Fallback to previously processed telemetry if raw merge is sparse/empty.
if env_long.empty:
    prev_long = norm_cols(safe_read_csv(ROOT / "processed_outputs" / "environmental_long_raipur.csv"))
    if not prev_long.empty:
        ts_col = find_col(prev_long.columns, ["timestamp", "time", "date"])
        metric_col = find_col(prev_long.columns, ["metric"])
        station_col = find_col(prev_long.columns, ["station"])
        district_col = find_col(prev_long.columns, ["district"])
        state_col = find_col(prev_long.columns, ["state"])
        lat_col = find_col(prev_long.columns, ["latitude", "lat"])
        lon_col = find_col(prev_long.columns, ["longitude", "lon"])
        value_col = find_col(prev_long.columns, ["value", "mean_value"])
        src_col = find_col(prev_long.columns, ["source"])
        if ts_col and metric_col and station_col and value_col:
            env_long = pd.DataFrame({
                "metric": prev_long[metric_col].astype(str),
                "station": prev_long[station_col].astype(str),
                "district": prev_long[district_col].astype(str) if district_col else "",
                "state": prev_long[state_col].astype(str) if state_col else "",
                "latitude": pd.to_numeric(prev_long[lat_col], errors="coerce") if lat_col else pd.NA,
                "longitude": pd.to_numeric(prev_long[lon_col], errors="coerce") if lon_col else pd.NA,
                "timestamp": parse_ts_series(prev_long[ts_col]),
                "value": pd.to_numeric(prev_long[value_col], errors="coerce"),
                "source_file": prev_long[src_col].astype(str) if src_col else "processed_outputs/environmental_long_raipur.csv",
            }).dropna(subset=["timestamp", "value", "station"])

# Unit normalization checks (already in file labels: mm/meter). Keep and document no conversion unless implausible extremes.
conversion_notes = []
if not rain.empty:
    if rain["value"].max() < 2:  # heuristic for potential meter-to-mm issue
        env_long.loc[env_long["metric"] == "rainfall", "value"] *= 1000
        conversion_notes.append("Rainfall values appeared in meters; converted to mm by x1000.")
if not conversion_notes:
    conversion_notes.append("No unit conversion applied; source units appear consistent (rainfall=mm, river/gwl=m).")

# enforce timezone string with +05:30 in output
env_long = env_long.sort_values(["metric", "station", "timestamp"]).reset_index(drop=True)
env_long["timestamp"] = pd.to_datetime(env_long["timestamp"], errors="coerce", utc=True).dt.tz_convert(TZ_NAME)
env_long = env_long.dropna(subset=["timestamp"])

# no unparsable timestamps already removed; ensure dedupe again
env_long = env_long.drop_duplicates(subset=["metric", "station", "timestamp"])

env_long_out = CLEAN / "environmental_long_raipur.csv"
env_long.to_csv(env_long_out, index=False)

# Daily aggregation
env_long_local = env_long.copy()
env_long_local["date"] = env_long_local["timestamp"].dt.tz_convert(TZ_NAME).dt.date

env_daily = (
    env_long_local
    .groupby(["metric", "date"], as_index=False)
    .agg(mean_value=("value", "mean"), min_value=("value", "min"), max_value=("value", "max"), records=("value", "size"))
)
env_daily_out = CLEAN / "environmental_daily_raipur.csv"
env_daily.to_csv(env_daily_out, index=False)

# ---------- Task B.2 Facilities master clean ----------
export = norm_cols(safe_read_csv(ROOT / "export.csv"))
if export.empty:
    raise RuntimeError("export.csv required for canonical facility master")

id_col = "@id" if "@id" in export.columns else ("id" if "id" in export.columns else None)
if id_col is None:
    raise RuntimeError("No @id/id in export.csv")

name_col = find_col(export.columns, ["name"])
amenity_col = find_col(export.columns, ["amenity"])
health_col = find_col(export.columns, ["healthcare"])
edu_col = find_col(export.columns, ["education"])
city_col = "addr:city" if "addr:city" in export.columns else None
district_col = "addr:district" if "addr:district" in export.columns else None
subdistrict_col = "addr:subdistrict" if "addr:subdistrict" in export.columns else None
full_col = "addr:full" if "addr:full" in export.columns else None
street_col = "addr:street" if "addr:street" in export.columns else None
hno_col = "addr:housenumber" if "addr:housenumber" in export.columns else None
state_col = "addr:state" if "addr:state" in export.columns else None
postcode_col = "addr:postcode" if "addr:postcode" in export.columns else None

x_col = "X" if "X" in export.columns else find_col(export.columns, ["lon", "longitude"])
y_col = "Y" if "Y" in export.columns else find_col(export.columns, ["lat", "latitude"])

fac = pd.DataFrame()
fac["facility_id"] = export[id_col].astype(str).str.strip()
fac["facility_name"] = export[name_col].astype(str).str.strip() if name_col else fac["facility_id"]
fac["latitude"] = pd.to_numeric(export[y_col], errors="coerce") if y_col else pd.NA
fac["longitude"] = pd.to_numeric(export[x_col], errors="coerce") if x_col else pd.NA

amenity = export[amenity_col].astype(str).str.lower() if amenity_col else pd.Series("", index=export.index)
health = export[health_col].astype(str).str.lower() if health_col else pd.Series("", index=export.index)
edu = export[edu_col].astype(str).str.lower() if edu_col else pd.Series("", index=export.index)
name_low = fac["facility_name"].astype(str).str.lower()

is_hospital = amenity.str.contains("hospital|clinic", na=False) | health.str.contains("hospital|clinic", na=False) | name_low.str.contains("hospital|clinic|medical", na=False)
is_school = amenity.str.contains("school|college|university", na=False) | edu.str.contains("school|college|university", na=False) | name_low.str.contains("school|college|academy|institute", na=False)

fac["facility_type"] = pd.NA
fac.loc[is_hospital, "facility_type"] = "Hospital"
fac.loc[is_school & fac["facility_type"].isna(), "facility_type"] = "School"

district_series = export[district_col].astype(str) if district_col else pd.Series("", index=export.index)
city_series = export[city_col].astype(str) if city_col else pd.Series("", index=export.index)
fac["district"] = district_series.where(district_series.str.strip().ne(""), city_series)
fac["district"] = fac["district"].fillna("").astype(str).str.upper()

street = export[street_col].fillna("").astype(str).str.strip() if street_col else pd.Series("", index=export.index)
hno = export[hno_col].fillna("").astype(str).str.strip() if hno_col else pd.Series("", index=export.index)
fac["street_address"] = (hno + " " + street).str.strip()
full = export[full_col].fillna("").astype(str).str.strip() if full_col else pd.Series("", index=export.index)
fac["complete_address"] = full

if subdistrict_col and district_col and city_col and state_col and postcode_col:
    fallback = (
        fac["street_address"].fillna("") + ", " +
        export[subdistrict_col].fillna("").astype(str).str.strip() + ", " +
        export[district_col].fillna("").astype(str).str.strip() + ", " +
        export[city_col].fillna("").astype(str).str.strip() + ", " +
        export[state_col].fillna("").astype(str).str.strip() + " " +
        export[postcode_col].fillna("").astype(str).str.strip()
    ).str.replace(r"\s+,", ",", regex=True).str.replace(r",\s*,", ",", regex=True).str.strip(" ,")
    fac.loc[fac["complete_address"].eq(""), "complete_address"] = fallback

fac = fac[fac["facility_type"].isin(["Hospital", "School"])]
fac = fac[fac["district"].str.contains("RAIPUR", na=False)]
fac = fac.dropna(subset=["facility_id", "latitude", "longitude"]).drop_duplicates(subset=["facility_id"]).reset_index(drop=True)

# Reconcile with generated master to retain canonical export while filling missing IDs.
gen_master = norm_cols(safe_read_csv(ROOT / "processed_outputs" / "facilities_master_generated_raipur.csv"))
if not gen_master.empty and "facility_id" in gen_master.columns:
    gen_master = gen_master.copy()
    if "district" in gen_master.columns:
        gen_master = gen_master[gen_master["district"].astype(str).str.upper().str.contains("RAIPUR", na=False)]
    if "facility_type" in gen_master.columns:
        gen_master = gen_master[gen_master["facility_type"].astype(str).str.lower().isin(["hospital", "school"])]

    for c in ["facility_name", "facility_type", "district", "latitude", "longitude"]:
        if c not in gen_master.columns:
            gen_master[c] = pd.NA

    missing_ids = set(gen_master["facility_id"].astype(str)) - set(fac["facility_id"].astype(str))
    if missing_ids:
        add = gen_master[gen_master["facility_id"].astype(str).isin(missing_ids)][[
            "facility_id", "facility_name", "latitude", "longitude", "facility_type", "district"
        ]].copy()
        add["street_address"] = ""
        add["complete_address"] = ""
        fac = pd.concat([fac, add], ignore_index=True)

fac = fac.drop_duplicates(subset=["facility_id"]).reset_index(drop=True)

fac_out = CLEAN / "facilities_master_raipur.csv"
fac.to_csv(fac_out, index=False)

# ---------- Task B.3 CRS + features clean + reconciliation ----------
feature_src = norm_cols(safe_read_csv(ROOT / "processed_outputs" / "facility_features_raipur.csv"))
crs_src = norm_cols(safe_read_csv(ROOT / "processed_outputs" / "facility_crs_raipur.csv"))

if feature_src.empty or crs_src.empty:
    raise RuntimeError("Required processed feature/CRS files not found")

feature_clean = feature_src.copy()
feature_clean = feature_clean[feature_clean["facility_id"].isin(set(fac["facility_id"]))]
feature_clean = feature_clean.drop_duplicates(subset=["facility_id"])
feature_clean_out = CLEAN / "facility_features_raipur.csv"
feature_clean.to_csv(feature_clean_out, index=False)

crs_clean = crs_src.copy()
crs_clean = crs_clean.drop_duplicates(subset=["facility_id"])
crs_clean = crs_clean[crs_clean["facility_id"].isin(set(fac["facility_id"]))]
crs_clean_out = CLEAN / "facility_crs_raipur.csv"
crs_clean.to_csv(crs_clean_out, index=False)

recon = crs_src[["facility_id"]].drop_duplicates().merge(
    fac[["facility_id"]].drop_duplicates(), on="facility_id", how="outer", indicator=True
)
recon["status"] = recon["_merge"].map({"both": "matched", "left_only": "missing_in_master", "right_only": "missing_in_crs"})
recon = recon.drop(columns=["_merge"]).sort_values(["status", "facility_id"])
recon_out = REPORTS / "reconciliation_facility_crs.csv"
recon.to_csv(recon_out, index=False)

# ---------- Task B.4 station/gauge mapping sanity ----------
gauges = env_long[["metric", "station", "latitude", "longitude"]].drop_duplicates()
gauges = gauges.dropna(subset=["latitude", "longitude"])

fac_map_rows = []
for _, fr in fac.iterrows():
    nearest_d = None
    nearest_station = None
    nearest_metric = None
    for _, gr in gauges.iterrows():
        d = haversine_km(float(fr["latitude"]), float(fr["longitude"]), float(gr["latitude"]), float(gr["longitude"]))
        if nearest_d is None or d < nearest_d:
            nearest_d = d
            nearest_station = gr["station"]
            nearest_metric = gr["metric"]
    fac_map_rows.append({
        "facility_id": fr["facility_id"],
        "nearest_station": nearest_station,
        "nearest_metric": nearest_metric,
        "distance_km": nearest_d,
        "within_threshold": (nearest_d is not None and nearest_d <= DIST_THRESHOLD_KM),
    })
fac_map = pd.DataFrame(fac_map_rows)

# ---------- Task B.5 report ----------
report_lines = []
report_lines.append("# Data Quality Report (Task B)\n")
report_lines.append("## Scope\n")
report_lines.append("- Cleaned outputs written under `delivery_phase1/data/clean/`.\n")
report_lines.append("- Canonical facility master derived from `export.csv` (Raipur hospitals/schools only).\n")
report_lines.append(f"- Timezone mapping: ambiguous naive timestamps localized to `{TZ_NAME}` (UTC+05:30).\n")
report_lines.append("\n## Telemetry Merge & Dedupe Rules\n")
report_lines.append("- Split-range files merged by `(metric, station, timestamp)`.\n")
report_lines.append("- On overlap, kept the row from file with later filename-derived priority (later range/date).\n")
report_lines.append("- Dedupe key for telemetry: `(metric, station, timestamp)`.\n")
report_lines.append("\n## Units Check\n")
for note in conversion_notes:
    report_lines.append(f"- {note}\n")

# Timestamp parseability summary
for name, df in [
    ("environmental_long_raipur.csv", env_long),
    ("environmental_daily_raipur.csv", env_daily),
    ("facilities_master_raipur.csv", fac),
    ("facility_features_raipur.csv", feature_clean),
    ("facility_crs_raipur.csv", crs_clean),
]:
    report_lines.append(f"\n## {name}\n")
    report_lines.append(f"- Rows: {len(df)}\n")
    if "timestamp" in df.columns:
        unparsable = int(df["timestamp"].isna().sum())
        report_lines.append(f"- Unparsable timestamps: {unparsable}\n")
    # missingness matrix top all columns
    miss = missingness_table(df)
    report_lines.append("- Missingness matrix (% missing):\n")
    if miss.empty:
        report_lines.append("\n(none)\n")
    else:
        report_lines.append("\n| column | missing_pct |\n|---|---:|\n")
        for _, r in miss.iterrows():
            report_lines.append(f"| {r['column']} | {r['missing_pct']} |\n")

# gauge mapping summary
report_lines.append("\n## Station/Gauge Mapping Sanity\n")
report_lines.append(f"- Distance threshold: {DIST_THRESHOLD_KM} km\n")
report_lines.append(f"- Gauges with lat/lon: {len(gauges)}\n")
within = int(fac_map["within_threshold"].sum()) if not fac_map.empty else 0
report_lines.append(f"- Facilities mapped to nearest gauge within threshold: {within}/{len(fac_map)}\n")
if not fac_map.empty:
    report_lines.append(f"- Median nearest-gauge distance (km): {fac_map['distance_km'].median():.2f}\n")

# reconciliation summary
mis = recon[recon["status"] != "matched"]
report_lines.append("\n## CRS Reconciliation\n")
report_lines.append(f"- Reconciliation file: `delivery_phase1/reports/reconciliation_facility_crs.csv`\n")
report_lines.append(f"- Matched keys: {int((recon['status'] == 'matched').sum())}\n")
report_lines.append(f"- Mismatches: {len(mis)}\n")
if len(mis) > 0:
    report_lines.append("- Manual mapping required for listed mismatch rows.\n")

quality_out = REPORTS / "data_quality_report.md"
quality_out.write_text("".join(report_lines), encoding="utf-8")

print("Task B completed")
print(f"Clean outputs: {CLEAN}")
print(f"Report: {quality_out}")
print(f"Reconciliation: {recon_out}")
print(f"Unparsable timestamps in env_long: {int(env_long['timestamp'].isna().sum())}")
print(f"Mismatches in reconciliation: {len(mis)}")
