from __future__ import annotations

from pathlib import Path
import math
import re
from typing import Iterable, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DELIVERY = ROOT / "delivery_phase1"
DATA_DIR = DELIVERY / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CLEAN_DIR = DATA_DIR / "clean"
REPORTS_DIR = DELIVERY / "reports"
DOCS_DIR = DELIVERY / "docs"
SCRIPTS_DIR = DELIVERY / "scripts"

for p in [PROCESSED_DIR, CLEAN_DIR, REPORTS_DIR, DOCS_DIR, SCRIPTS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

TZ_NAME = "Asia/Kolkata"


def safe_read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def safe_read_xlsx(path: Path) -> pd.DataFrame:
    try:
        return pd.read_excel(path)
    except Exception:
        return pd.DataFrame()


def norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


def find_col(cols: Iterable[str], options: Iterable[str]) -> Optional[str]:
    lowered = {str(c).lower(): c for c in cols}
    for opt in options:
        for k, v in lowered.items():
            if opt in k:
                return v
    return None


def parse_ts_series(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()

    def _parse_one(v: str):
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


def file_priority(name: str) -> int:
    score = 0
    m = re.search(r"(\d{4})-(\d{4})", name)
    if m:
        score += int(m.group(2))
    d = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    if d:
        score += int(d.group(1).replace("-", ""))
    return score


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def ensure_facility_master() -> Path:
    """Build or return canonical facility master in processed dir."""
    out_path = PROCESSED_DIR / "facilities_master_raipur.csv"
    if out_path.exists():
        return out_path

    export = norm_cols(safe_read_csv(ROOT / "export.csv"))
    gen = norm_cols(safe_read_csv(ROOT / "processed_outputs" / "facilities_master_generated_raipur.csv"))

    if export.empty and gen.empty:
        raise RuntimeError("No facility source found (export.csv or generated master)")

    if not export.empty:
        id_col = "@id" if "@id" in export.columns else ("id" if "id" in export.columns else None)
        if id_col is None:
            raise RuntimeError("export.csv missing @id/id")

        x_col = "X" if "X" in export.columns else find_col(export.columns, ["lon", "longitude"])
        y_col = "Y" if "Y" in export.columns else find_col(export.columns, ["lat", "latitude"])
        name_col = find_col(export.columns, ["name"])
        amenity_col = find_col(export.columns, ["amenity"])
        healthcare_col = find_col(export.columns, ["healthcare"])
        education_col = find_col(export.columns, ["education"])

        fac = pd.DataFrame()
        fac["facility_id"] = export[id_col].astype(str).str.strip()
        fac["facility_name"] = export[name_col].astype(str).str.strip() if name_col else fac["facility_id"]
        fac["latitude"] = pd.to_numeric(export[y_col], errors="coerce") if y_col else pd.NA
        fac["longitude"] = pd.to_numeric(export[x_col], errors="coerce") if x_col else pd.NA

        amenity = export[amenity_col].astype(str).str.lower() if amenity_col else pd.Series("", index=export.index)
        health = export[healthcare_col].astype(str).str.lower() if healthcare_col else pd.Series("", index=export.index)
        edu = export[education_col].astype(str).str.lower() if education_col else pd.Series("", index=export.index)
        nlow = fac["facility_name"].astype(str).str.lower()

        is_h = amenity.str.contains("hospital|clinic", na=False) | health.str.contains("hospital|clinic", na=False) | nlow.str.contains("hospital|clinic|medical", na=False)
        is_s = amenity.str.contains("school|college|university", na=False) | edu.str.contains("school|college|university", na=False) | nlow.str.contains("school|college|academy|institute", na=False)

        fac["facility_type"] = pd.NA
        fac.loc[is_h, "facility_type"] = "Hospital"
        fac.loc[is_s & fac["facility_type"].isna(), "facility_type"] = "School"

        district = export["addr:district"].astype(str) if "addr:district" in export.columns else pd.Series("", index=export.index)
        city = export["addr:city"].astype(str) if "addr:city" in export.columns else pd.Series("", index=export.index)
        fac["district"] = district.where(district.str.strip().ne(""), city).fillna("").astype(str).str.upper()

        street = export["addr:street"].fillna("").astype(str).str.strip() if "addr:street" in export.columns else pd.Series("", index=export.index)
        hno = export["addr:housenumber"].fillna("").astype(str).str.strip() if "addr:housenumber" in export.columns else pd.Series("", index=export.index)
        fac["street_address"] = (hno + " " + street).str.strip()
        full = export["addr:full"].fillna("").astype(str).str.strip() if "addr:full" in export.columns else pd.Series("", index=export.index)
        fac["complete_address"] = full

        fac = fac[fac["facility_type"].isin(["Hospital", "School"])]
        fac = fac[fac["district"].str.contains("RAIPUR", na=False)]
        fac = fac.dropna(subset=["facility_id", "latitude", "longitude"]).drop_duplicates(subset=["facility_id"])
    else:
        fac = gen.copy()
        if "district" in fac.columns:
            fac = fac[fac["district"].astype(str).str.upper().str.contains("RAIPUR", na=False)]
        if "facility_type" in fac.columns:
            fac = fac[fac["facility_type"].astype(str).str.lower().isin(["hospital", "school"])]
        for c in ["street_address", "complete_address"]:
            if c not in fac.columns:
                fac[c] = ""

    if not gen.empty and "facility_id" in gen.columns:
        missing = set(gen["facility_id"].astype(str)) - set(fac["facility_id"].astype(str))
        if missing:
            add = gen[gen["facility_id"].astype(str).isin(missing)].copy()
            for c in ["street_address", "complete_address"]:
                if c not in add.columns:
                    add[c] = ""
            keep_cols = [c for c in fac.columns if c in add.columns]
            fac = pd.concat([fac, add[keep_cols]], ignore_index=True)

    fac = fac.drop_duplicates(subset=["facility_id"]).reset_index(drop=True)
    fac.to_csv(out_path, index=False)
    return out_path
