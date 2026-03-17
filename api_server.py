"""
FastAPI backend for ClimaSafe Infrastructure Risk Monitoring.
Reads existing CSV/JSON data files and serves them as REST endpoints
aligned with the React frontend's API contracts.
"""
from __future__ import annotations

import glob
import json
import math
import os
from pathlib import Path
from typing import Any
from urllib import error, parse, request

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "processed_outputs"
CLEAN = ROOT / "delivery_phase1" / "data" / "clean"


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, value = s.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(ROOT / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
SUPABASE_REST_URL = f"{SUPABASE_URL.rstrip('/')}/rest/v1" if SUPABASE_URL else ""


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "*").strip()
    if not raw:
        return ["*"]
    return [item.strip() for item in raw.split(",") if item.strip()]

# ── App setup ──────────────────────────────────────────────────────────────────
app = FastAPI(title="ClimaSafe API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Data loading (once at startup) ─────────────────────────────────────────────

def _safe_read(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def _label(prob: float) -> str:
    if prob >= 0.7:
        return "High"
    if prob >= 0.4:
        return "Medium"
    return "Low"


def _supabase_get(
    table: str,
    *,
    select: str = "*",
    filters: dict[str, str] | None = None,
    order: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    if not SUPABASE_REST_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return []

    query: dict[str, str] = {"select": select}
    if filters:
        query.update(filters)
    if order:
        query["order"] = order
    if limit is not None:
        query["limit"] = str(limit)

    url = f"{SUPABASE_REST_URL}/{table}?{parse.urlencode(query, safe='.,:*()')}"
    req = request.Request(
        url,
        headers={
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    )
    try:
        with request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list):
                return data
            return []
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        print(f"[ClimaSafe API] Supabase HTTP error on {table}: {exc.code} {body}")
    except Exception as exc:
        print(f"[ClimaSafe API] Supabase request failed on {table}: {exc}")
    return []


def _load_facilities_from_supabase() -> list[dict[str, Any]]:
    base_rows = _supabase_get(
        "facilities",
        select="facility_id,facility_name,facility_type,district,latitude,longitude,complete_address,street_address,city,state,postcode",
    )
    risk_rows = _supabase_get(
        "v_latest_facility_risk",
        select=(
            "facility_id,crs,risk_level,gwl_value,rainfall_value,river_level_value,outage_risk,"
            "pred_outage_prob_24h,pred_outage_prob_7d,water_availability,flood_safety,"
            "rainfall_stability,electricity_reliability,flood_risk_prob,water_shortage_risk_prob,"
            "power_outage_risk_prob,sanitation_failure_risk_prob,flood_risk_label,"
            "water_shortage_risk_label,power_outage_risk_label,sanitation_failure_risk_label,"
            "top_risk_type,top_risk_score,alert_flag,alert_level,prediction_ts"
        ),
    )

    if not base_rows and not risk_rows:
        return []

    base_by_id = {
        str(row.get("facility_id", "")): row
        for row in base_rows
        if row.get("facility_id") is not None
    }

    facilities: list[dict[str, Any]] = []
    for risk in risk_rows:
        facility_id = str(risk.get("facility_id", ""))
        base = base_by_id.get(facility_id, {})

        water_avail = float(_nan_to_default(risk.get("water_availability"), 0.5))
        flood_safety = float(_nan_to_default(risk.get("flood_safety"), 0.5))
        rainfall_stab = float(_nan_to_default(risk.get("rainfall_stability"), 0.5))
        elec_rel = float(_nan_to_default(risk.get("electricity_reliability"), 0.5))

        flood_risk_prob = float(_nan_to_default(risk.get("flood_risk_prob"), 1.0 - flood_safety))
        water_shortage_prob = float(_nan_to_default(risk.get("water_shortage_risk_prob"), 1.0 - water_avail))
        power_outage_prob = float(_nan_to_default(risk.get("power_outage_risk_prob"), 1.0 - elec_rel))
        sanitation_prob = float(
            _nan_to_default(
                risk.get("sanitation_failure_risk_prob"),
                max(0.0, 1.0 - (rainfall_stab * 0.6 + water_avail * 0.4)),
            )
        )

        top_risk_type = str(_nan_to_default(risk.get("top_risk_type"), "flood_risk"))
        top_risk_score = float(_nan_to_default(risk.get("top_risk_score"), flood_risk_prob))
        risk_level = str(_nan_to_default(risk.get("risk_level"), _label(top_risk_score)))
        alert_flag = bool(_nan_to_default(risk.get("alert_flag"), False))

        fac: dict[str, Any] = {
            "facility_id": facility_id,
            "facility_name": str(_nan_to_default(base.get("facility_name"), facility_id)),
            "facility_type": str(_nan_to_default(base.get("facility_type"), "Hospital")),
            "district": str(_nan_to_default(base.get("district"), "")),
            "latitude": float(_nan_to_default(base.get("latitude"), 21.25)),
            "longitude": float(_nan_to_default(base.get("longitude"), 81.63)),
            "crs": round(float(_nan_to_default(risk.get("crs"), 0.5)), 4),
            "risk_level": risk_level,
            "gwl_value": _nan_to_default(risk.get("gwl_value"), 0),
            "rainfall_value": _nan_to_default(risk.get("rainfall_value"), 0),
            "river_level_value": _nan_to_default(risk.get("river_level_value"), 0),
            "outage_risk": float(_nan_to_default(risk.get("outage_risk"), 0.5)),
            "pred_outage_prob_24h": round(float(_nan_to_default(risk.get("pred_outage_prob_24h"), 0.5)), 4),
            "pred_outage_prob_7d": round(float(_nan_to_default(risk.get("pred_outage_prob_7d"), 0.5)), 4),
            "water_availability": round(water_avail, 4),
            "flood_safety": round(flood_safety, 4),
            "rainfall_stability": round(rainfall_stab, 4),
            "electricity_reliability": round(elec_rel, 4),
            "flood_risk_prob": round(flood_risk_prob, 4),
            "water_shortage_risk_prob": round(water_shortage_prob, 4),
            "power_outage_risk_prob": round(power_outage_prob, 4),
            "sanitation_failure_risk_prob": round(sanitation_prob, 4),
            "flood_risk_label": str(_nan_to_default(risk.get("flood_risk_label"), _label(flood_risk_prob))),
            "water_shortage_risk_label": str(_nan_to_default(risk.get("water_shortage_risk_label"), _label(water_shortage_prob))),
            "power_outage_risk_label": str(_nan_to_default(risk.get("power_outage_risk_label"), _label(power_outage_prob))),
            "sanitation_failure_risk_label": str(_nan_to_default(risk.get("sanitation_failure_risk_label"), _label(sanitation_prob))),
            "top_risk_type": top_risk_type,
            "top_risk_score": round(top_risk_score, 4),
            "alert_flag": alert_flag,
            "alert_level": str(_nan_to_default(risk.get("alert_level"), "Normal")),
            "complete_address": str(_nan_to_default(base.get("complete_address"), "")),
            "street_address": str(_nan_to_default(base.get("street_address"), "")),
            "addr:city": str(_nan_to_default(base.get("city"), "")),
            "addr:state": str(_nan_to_default(base.get("state"), "")),
            "addr:postcode": str(_nan_to_default(base.get("postcode"), "")),
            "last_updated": str(_nan_to_default(risk.get("prediction_ts"), "")),
        }
        facilities.append(fac)

    return facilities


def _load_climate_trends_from_supabase() -> list[dict[str, Any]]:
    rows = _supabase_get(
        "climate_trends_monthly",
        select="metric,month,value",
        order="month.asc",
    )
    result: list[dict[str, Any]] = []
    for row in rows:
        month = str(_nan_to_default(row.get("month"), ""))
        month = month[:7] if len(month) >= 7 else month
        result.append(
            {
                "metric": str(_nan_to_default(row.get("metric"), "")),
                "month": month,
                "value": round(float(_nan_to_default(row.get("value"), 0)), 4),
            }
        )
    return result


def _load_weather_from_supabase() -> dict[str, Any] | None:
    rows = _supabase_get(
        "weather_snapshots",
        select="provider,city,fetched_at,payload",
        order="fetched_at.desc",
        limit=1,
    )
    if not rows:
        return None
    row = rows[0]
    payload = row.get("payload")
    if isinstance(payload, dict) and "current_weather" in payload:
        return payload
    return {
        "meta": {"fetched_at_utc": row.get("fetched_at")},
        "provider": row.get("provider", "Supabase"),
        "city": row.get("city", "Raipur"),
        "current_weather": {"payload": payload if isinstance(payload, dict) else {}},
    }


def _nan_to_default(val: Any, default: Any = 0) -> Any:
    """Replace NaN / None with a sensible default."""
    if val is None:
        return default
    try:
        if math.isnan(val):
            return default
    except (TypeError, ValueError):
        pass
    return val


def _load_facilities() -> list[dict]:
    """
    Merge facility_features + outage_risk + crs_predictions into the
    complete Facility object the frontend expects.
    """
    features = _safe_read(PROCESSED / "facility_features_raipur.csv")
    outage = _safe_read(PROCESSED / "raipur_facility_outage_risk_24h.csv")
    crs_pred = _safe_read(PROCESSED / "crs_predictions_raipur_facilities.csv")

    if features.empty:
        # Fallback to clean directory
        features = _safe_read(CLEAN / "facility_features_raipur.csv")

    if features.empty:
        return []

    # Merge outage predictions
    if not outage.empty and "facility_id" in outage.columns:
        outage_cols = ["facility_id"]
        if "pred_outage_prob_24h" in outage.columns:
            outage_cols.append("pred_outage_prob_24h")
        if "priority_score" in outage.columns:
            outage_cols.append("priority_score")
        features = features.merge(
            outage[outage_cols], on="facility_id", how="left", suffixes=("", "_outage")
        )

    # Merge address info from crs_predictions
    if not crs_pred.empty and "facility_id" in crs_pred.columns:
        addr_cols = ["facility_id"]
        for c in [
            "complete_address", "street_address",
            "addr:city", "addr:state", "addr:postcode",
            "addr:district", "addr:subdistrict",
        ]:
            if c in crs_pred.columns:
                addr_cols.append(c)
        features = features.merge(
            crs_pred[addr_cols], on="facility_id", how="left", suffixes=("", "_crs")
        )

    facilities = []
    for _, row in features.iterrows():
        # Derive multi-risk probabilities from sub-component scores
        water_avail = _nan_to_default(row.get("water_availability"), 0.5)
        flood_safety = _nan_to_default(row.get("flood_safety"), 0.5)
        rainfall_stab = _nan_to_default(row.get("rainfall_stability"), 0.5)
        elec_rel = _nan_to_default(row.get("electricity_reliability"), 0.5)
        crs = _nan_to_default(row.get("crs"), 0.5)

        # Multi-risk probabilities: inverse of sub-component safety scores
        flood_risk_prob = round(1.0 - flood_safety, 4)
        water_shortage_prob = round(1.0 - water_avail, 4)
        power_outage_prob = round(1.0 - elec_rel, 4)
        sanitation_prob = round(max(0, 1.0 - (rainfall_stab * 0.6 + water_avail * 0.4)), 4)

        # Top risk
        risk_map = {
            "flood_risk": flood_risk_prob,
            "water_shortage": water_shortage_prob,
            "power_outage": power_outage_prob,
            "sanitation_failure": sanitation_prob,
        }
        top_risk_type = max(risk_map, key=risk_map.get)  # type: ignore
        top_risk_score = risk_map[top_risk_type]

        # Alert logic
        risk_level = str(row.get("risk_level", "Medium"))
        alert_flag = risk_level == "High" or top_risk_score >= 0.7
        if risk_level == "High" and top_risk_score >= 0.7:
            alert_level = "Critical"
        elif alert_flag:
            alert_level = "High"
        else:
            alert_level = "Normal"

        pred_24h = _nan_to_default(row.get("pred_outage_prob_24h"), 0.5)

        fac: dict[str, Any] = {
            "facility_id": str(row.get("facility_id", "")),
            "facility_name": str(row.get("facility_name", "")),
            "facility_type": str(row.get("facility_type", "Hospital")),
            "district": str(row.get("district", "")),
            "latitude": _nan_to_default(row.get("latitude"), 21.25),
            "longitude": _nan_to_default(row.get("longitude"), 81.63),
            # CRS
            "crs": round(crs, 4),
            "risk_level": risk_level,
            # Environmental
            "gwl_value": _nan_to_default(row.get("gwl_value"), 0),
            "rainfall_value": _nan_to_default(row.get("rainfall_value"), 0),
            "river_level_value": _nan_to_default(row.get("river_level_value"), 0),
            # Outage
            "outage_risk": _nan_to_default(row.get("outage_risk"), 0.5),
            "pred_outage_prob_24h": round(pred_24h, 4),
            "pred_outage_prob_7d": round(pred_24h * 0.85, 4),
            # Sub-component scores
            "water_availability": round(water_avail, 4),
            "flood_safety": round(flood_safety, 4),
            "rainfall_stability": round(rainfall_stab, 4),
            "electricity_reliability": round(elec_rel, 4),
            # Multi-risk probabilities
            "flood_risk_prob": flood_risk_prob,
            "water_shortage_risk_prob": water_shortage_prob,
            "power_outage_risk_prob": power_outage_prob,
            "sanitation_failure_risk_prob": sanitation_prob,
            # Multi-risk labels
            "flood_risk_label": _label(flood_risk_prob),
            "water_shortage_risk_label": _label(water_shortage_prob),
            "power_outage_risk_label": _label(power_outage_prob),
            "sanitation_failure_risk_label": _label(sanitation_prob),
            # Aggregate
            "top_risk_type": top_risk_type,
            "top_risk_score": round(top_risk_score, 4),
            "alert_flag": alert_flag,
            "alert_level": alert_level,
            # Address
            "complete_address": str(_nan_to_default(row.get("complete_address"), "")),
            "street_address": str(_nan_to_default(row.get("street_address"), "")),
            "addr:city": str(_nan_to_default(row.get("addr:city"), "")),
            "addr:state": str(_nan_to_default(row.get("addr:state"), "")),
            "addr:postcode": str(_nan_to_default(row.get("addr:postcode"), "")),
            "last_updated": str(_nan_to_default(row.get("last_updated"), "")),
        }
        # Clean 'nan' strings
        for k, v in fac.items():
            if isinstance(v, str) and v.lower() == "nan":
                fac[k] = ""

        facilities.append(fac)

    return facilities


def _load_env_daily() -> pd.DataFrame:
    df = _safe_read(PROCESSED / "environmental_daily_raipur.csv")
    if df.empty:
        df = _safe_read(CLEAN / "environmental_daily_raipur.csv")
    return df


def _load_weather() -> dict | None:
    pattern = str(PROCESSED / "openweather_snapshot_*.json")
    files = sorted(glob.glob(pattern))
    if not files:
        # Fallback to weather_snapshot
        pattern = str(PROCESSED / "weather_snapshot_*.json")
        files = sorted(glob.glob(pattern))
    if not files:
        return None
    with open(files[-1], "r") as f:
        return json.load(f)


# ── Global data cache ──────────────────────────────────────────────────────────
FACILITIES: list[dict] = []
ENV_DAILY: pd.DataFrame = pd.DataFrame()
WEATHER_DATA: dict | None = None
CLIMATE_TRENDS: list[dict[str, Any]] = []


@app.on_event("startup")
def startup():
    global FACILITIES, ENV_DAILY, WEATHER_DATA, CLIMATE_TRENDS

    supabase_facilities = _load_facilities_from_supabase()
    supabase_climate = _load_climate_trends_from_supabase()
    supabase_weather = _load_weather_from_supabase()

    if supabase_facilities or supabase_climate or supabase_weather:
        FACILITIES = supabase_facilities
        CLIMATE_TRENDS = supabase_climate
        WEATHER_DATA = supabase_weather
        ENV_DAILY = pd.DataFrame()
        print("[ClimaSafe API] Data source: Supabase")
    else:
        FACILITIES = _load_facilities()
        ENV_DAILY = _load_env_daily()
        WEATHER_DATA = _load_weather()
        CLIMATE_TRENDS = []
        print("[ClimaSafe API] Data source: Local files")

    print(f"[ClimaSafe API] Loaded {len(FACILITIES)} facilities")
    print(f"[ClimaSafe API] Climate monthly rows: {len(CLIMATE_TRENDS)}")
    print(f"[ClimaSafe API] Env daily rows: {len(ENV_DAILY)}")
    print(f"[ClimaSafe API] Weather snapshot: {'loaded' if WEATHER_DATA else 'not found'}")


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/api/facilities")
def get_facilities():
    return FACILITIES


@app.get("/api/facilities/{facility_id:path}")
def get_facility(facility_id: str):
    """
    Get a single facility by ID. 
    Handles IDs like 'node/3774564938' via path parameter.
    Also handles the /explain sub-path.
    """
    # Check if it's an explain request
    if facility_id.endswith("/explain"):
        real_id = facility_id[:-len("/explain")]
        return _get_explanation(real_id)

    for fac in FACILITIES:
        if fac["facility_id"] == facility_id:
            return fac
    raise HTTPException(status_code=404, detail=f"Facility '{facility_id}' not found")


@app.get("/api/risk-summary")
def get_risk_summary():
    total = len(FACILITIES)
    high = sum(1 for f in FACILITIES if f["risk_level"] == "High")
    medium = sum(1 for f in FACILITIES if f["risk_level"] == "Medium")
    low = sum(1 for f in FACILITIES if f["risk_level"] == "Low")
    return {"total": total, "high": high, "medium": medium, "low": low}


@app.get("/api/climate-trends")
def get_climate_trends():
    """
    Return monthly aggregated environmental data:
    [{metric, month, value}, ...]
    """
    if CLIMATE_TRENDS:
        return CLIMATE_TRENDS

    if ENV_DAILY.empty:
        return []

    df = ENV_DAILY.copy()
    # Ensure date column
    if "date" not in df.columns:
        return []

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["month"] = df["date"].dt.to_period("M").astype(str)

    # Use mean_value column
    val_col = "mean_value" if "mean_value" in df.columns else "value"
    if val_col not in df.columns:
        return []

    grouped = df.groupby(["metric", "month"])[val_col].mean().reset_index()
    grouped.columns = ["metric", "month", "value"]

    result = []
    for _, row in grouped.iterrows():
        result.append({
            "metric": str(row["metric"]),
            "month": str(row["month"]),
            "value": round(float(_nan_to_default(row["value"], 0)), 4),
        })

    return result


@app.get("/api/district-data")
def get_district_data():
    """
    Return facility counts by district: [{district, schools, hospitals}, ...]
    """
    districts: dict[str, dict[str, int]] = {}
    for fac in FACILITIES:
        d = fac["district"]
        if d not in districts:
            districts[d] = {"schools": 0, "hospitals": 0}
        if fac["facility_type"] == "School":
            districts[d]["schools"] += 1
        elif fac["facility_type"] == "Hospital":
            districts[d]["hospitals"] += 1

    return [
        {"district": d, "schools": c["schools"], "hospitals": c["hospitals"]}
        for d, c in sorted(districts.items())
    ]


@app.get("/api/forecast/{facility_id:path}")
def get_forecast(facility_id: str):
    """
    Generate a synthetic but realistic 7-day risk forecast.
    Risks are jittered around the base risk values of the facility.
    """
    from datetime import datetime, timedelta
    import random

    fac = None
    for f in FACILITIES:
        if f["facility_id"] == facility_id:
            fac = f
            break

    if fac is None:
        raise HTTPException(status_code=404, detail=f"Facility '{facility_id}' not found")

    base_flood = fac["flood_risk_prob"]
    base_water = fac["water_shortage_risk_prob"]
    base_power = fac["power_outage_risk_prob"]
    base_sanitation = fac["sanitation_failure_risk_prob"]

    forecast = []
    today = datetime.now()

    # Determine a "trend" for the 7 days
    # Let's say there's a 30% chance of an upcoming weather event that peaks in the middle
    events = [
        {"type": "None", "peak_day": 0, "magnitude": 0},
        {"type": "Heavy Rain", "peak_day": random.randint(2, 5), "magnitude": 0.25},
        {"type": "Heatwave", "peak_day": random.randint(2, 5), "magnitude": 0.20},
    ]
    event = random.choice(events)

    for i in range(7):
        date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        
        # Calculate impact of event based on proximity to peak day
        dist = abs(i - event["peak_day"])
        impact = max(0, event["magnitude"] * (1 - dist/3))

        # Add some noise
        def _jitter(base, imp):
            v = base + imp + random.uniform(-0.05, 0.05)
            return round(max(0, min(1, v)), 4)

        f_flood = _jitter(base_flood, impact if event["type"] == "Heavy Rain" else 0)
        f_water = _jitter(base_water, impact if event["type"] == "Heatwave" else 0)
        f_power = _jitter(base_power, impact * 0.5) # Power affected by both rain and heat
        f_sanitation = _jitter(base_sanitation, impact * 0.7 if event["type"] == "Heavy Rain" else 0)

        overall_prob = max(f_flood, f_water, f_power, f_sanitation)
        
        if overall_prob >= 0.7:
            level = "High"
        elif overall_prob >= 0.4:
            level = "Medium"
        else:
            level = "Low"

        forecast.append({
            "facility_name": fac["facility_name"],
            "date": date,
            "day": i + 1,
            "flood_risk_probability": f_flood,
            "water_shortage_probability": f_water,
            "power_outage_probability": f_power,
            "sanitation_failure_probability": f_sanitation,
            "overall_risk_level": level,
            "overall_risk_probability": overall_prob
        })

    # AI Insight generation based on the mock event
    insight = "Overall risks are stable based on current indicators."
    if event["type"] == "Heavy Rain":
        insight = "High flood risk predicted due to heavy rainfall forecast and rising river levels in the coming days."
    elif event["type"] == "Heatwave":
        insight = "Increased water shortage and power grid stress predicted due to forecasted temperature spikes."

    return {
        "facility_id": facility_id,
        "facility_name": fac["facility_name"],
        "forecast": forecast,
        "ai_insight": insight
    }


@app.get("/api/alerts")
def get_alerts():
    """
    Return alerts for facilities with alert_flag=true.
    Maps to the Alert interface expected by the frontend.
    """
    RISK_DESCRIPTIONS = {
        "flood_risk": {
            "issue": "Elevated flood risk due to high river levels and heavy rainfall patterns",
            "action": "Activate flood preparedness protocols; inspect drainage systems and stock emergency supplies",
        },
        "water_shortage": {
            "issue": "Declining groundwater levels indicate potential water supply disruption",
            "action": "Implement water conservation measures; ensure backup water supply is operational",
        },
        "power_outage": {
            "issue": "High probability of power outage based on infrastructure reliability assessment",
            "action": "Verify backup generators are operational; test UPS systems and fuel reserves",
        },
        "sanitation_failure": {
            "issue": "Sanitation systems at risk due to combined environmental stressors",
            "action": "Inspect sanitation infrastructure; prepare contingency waste management plans",
        },
    }

    alerts = []
    for fac in FACILITIES:
        if not fac.get("alert_flag"):
            continue

        risk_type = fac.get("top_risk_type", "flood_risk")
        desc = RISK_DESCRIPTIONS.get(risk_type, RISK_DESCRIPTIONS["flood_risk"])

        alerts.append({
            "id": fac["facility_id"],
            "facilityId": fac["facility_id"],
            "facilityName": fac["facility_name"],
            "facilityType": fac["facility_type"],
            "riskLevel": fac["alert_level"],
            "topRiskType": risk_type,
            "topRiskScore": fac["top_risk_score"],
            "predictedIssue": desc["issue"],
            "recommendedAction": desc["action"],
            "timestamp": fac.get("last_updated", ""),
        })

    # Sort: Critical first, then High, then by score descending
    level_order = {"Critical": 0, "High": 1, "Normal": 2}
    alerts.sort(key=lambda a: (level_order.get(a["riskLevel"], 9), -a["topRiskScore"]))

    return alerts


@app.get("/api/weather")
def get_weather():
    """Return latest weather snapshot data."""
    if WEATHER_DATA is None:
        return {"error": "No weather data available"}

    # Extract current weather summary
    result: dict[str, Any] = {"provider": "OpenWeather", "city": "Raipur"}

    current = WEATHER_DATA.get("current_weather", {})
    if not isinstance(current, dict):
        current = {}
    payload = current.get("payload", {})
    if not payload and isinstance(WEATHER_DATA.get("payload"), dict):
        payload = WEATHER_DATA["payload"]
    if payload:
        main = payload.get("main", {})
        wind = payload.get("wind", {})
        weather_list = payload.get("weather", [{}])
        weather_desc = weather_list[0] if weather_list else {}

        result.update({
            "temperature": main.get("temp"),
            "feels_like": main.get("feels_like"),
            "humidity": main.get("humidity"),
            "pressure": main.get("pressure"),
            "wind_speed": wind.get("speed"),
            "wind_deg": wind.get("deg"),
            "description": weather_desc.get("description", ""),
            "icon": weather_desc.get("icon", ""),
            "visibility": payload.get("visibility"),
        })

    meta = WEATHER_DATA.get("meta", {}) if isinstance(WEATHER_DATA.get("meta", {}), dict) else {}
    result["fetched_at"] = meta.get("fetched_at_utc", WEATHER_DATA.get("fetched_at", ""))
    return result


@app.get("/api/health")
def get_health():
    return {
        "status": "ok",
        "source": "supabase" if CLIMATE_TRENDS or (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY and FACILITIES) else "local",
        "facilities": len(FACILITIES),
    }


def _get_explanation(facility_id: str) -> dict:
    """
    Generate XAI explanation for a facility.
    Uses feature values to compute SHAP-style explanations.
    """
    fac = None
    for f in FACILITIES:
        if f["facility_id"] == facility_id:
            fac = f
            break

    if fac is None:
        raise HTTPException(status_code=404, detail=f"Facility '{facility_id}' not found")

    top_risk_type = fac["top_risk_type"]
    top_risk_score = fac["top_risk_score"]
    risk_label = fac.get(f"{top_risk_type}_risk_label", fac["risk_level"]) if f"{top_risk_type}_risk_label" in fac else fac["risk_level"]

    # Build explanations from sub-component scores
    # Each factor shows how it contributes to the overall risk
    factors = [
        {
            "factor": "Groundwater Level",
            "key": "gwl_value",
            "icon": "💧",
            "raw_value": f"{fac['gwl_value']:.2f} m",
            "contribution": 0,
            "direction": "increases_risk",
        },
        {
            "factor": "Rainfall",
            "key": "rainfall_value",
            "icon": "🌧️",
            "raw_value": f"{fac['rainfall_value']:.2f} mm",
            "contribution": 0,
            "direction": "increases_risk",
        },
        {
            "factor": "River Water Level",
            "key": "river_level_value",
            "icon": "🌊",
            "raw_value": f"{fac['river_level_value']:.2f} m",
            "contribution": 0,
            "direction": "increases_risk",
        },
        {
            "factor": "Water Availability",
            "key": "water_availability",
            "icon": "🚰",
            "raw_value": f"{fac['water_availability'] * 100:.0f}%",
            "contribution": 0,
            "direction": "decreases_risk",
        },
        {
            "factor": "Flood Safety",
            "key": "flood_safety",
            "icon": "🛡️",
            "raw_value": f"{fac['flood_safety'] * 100:.0f}%",
            "contribution": 0,
            "direction": "decreases_risk",
        },
        {
            "factor": "Electricity Reliability",
            "key": "electricity_reliability",
            "icon": "⚡",
            "raw_value": f"{fac['electricity_reliability'] * 100:.0f}%",
            "contribution": 0,
            "direction": "decreases_risk",
        },
        {
            "factor": "Rainfall Stability",
            "key": "rainfall_stability",
            "icon": "📊",
            "raw_value": f"{fac['rainfall_stability'] * 100:.0f}%",
            "contribution": 0,
            "direction": "decreases_risk",
        },
        {
            "factor": "24h Outage Probability",
            "key": "pred_outage_prob_24h",
            "icon": "🔌",
            "raw_value": f"{fac['pred_outage_prob_24h'] * 100:.0f}%",
            "contribution": 0,
            "direction": "increases_risk",
        },
    ]

    # Compute contributions based on how each factor deviates from safe baseline
    # Higher absolute contribution = more influence on the risk score
    baselines = {
        "gwl_value": -5.0,  # typical safe GWL depth
        "rainfall_value": 2.0,  # typical normal rainfall
        "river_level_value": 200.0,  # typical safe river level
        "water_availability": 0.7,  # good availability
        "flood_safety": 0.7,  # good safety
        "electricity_reliability": 0.7,  # good reliability
        "rainfall_stability": 0.8,  # good stability
        "pred_outage_prob_24h": 0.3,  # acceptable outage prob
    }

    total_abs_contribution = 0
    for f in factors:
        key = f["key"]
        val = fac.get(key, 0)
        baseline = baselines.get(key, 0.5)

        if f["direction"] == "increases_risk":
            # Higher value = more risk contribution
            delta = val - baseline
            f["contribution"] = delta
        else:
            # Lower value = more risk contribution (inverted)
            delta = baseline - val
            f["contribution"] = delta

        # Determine final direction based on actual contribution
        if f["contribution"] < 0:
            f["direction"] = "decreases_risk"
            f["contribution"] = abs(f["contribution"])
        else:
            f["direction"] = "increases_risk"

        total_abs_contribution += abs(f["contribution"])

    # Normalize contributions to percentages
    for f in factors:
        if total_abs_contribution > 0:
            f["contribution_pct"] = round(f["contribution"] / total_abs_contribution * 100, 1)
        else:
            f["contribution_pct"] = round(100.0 / len(factors), 1)
        f["contribution"] = round(f["contribution"], 4)

    # Sort by absolute contribution (most impactful first)
    factors.sort(key=lambda x: x["contribution_pct"], reverse=True)

    confidence = min(0.95, 0.5 + top_risk_score * 0.4)

    return {
        "facility_id": fac["facility_id"],
        "facility_name": fac["facility_name"],
        "facility_type": fac["facility_type"],
        "top_risk_type": top_risk_type,
        "top_risk_label": risk_label,
        "top_risk_score": round(top_risk_score, 4),
        "top_risk_score_pct": round(top_risk_score * 100, 1),
        "confidence": round(confidence, 4),
        "confidence_pct": round(confidence * 100, 1),
        "explanations": factors,
    }


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
