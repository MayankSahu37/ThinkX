from __future__ import annotations

import glob
import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, parse, request
from uuid import uuid4

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "processed_outputs"


def load_dotenv(path: Path) -> None:
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


load_dotenv(ROOT / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_REST_URL = f"{SUPABASE_URL}/rest/v1" if SUPABASE_URL else ""


def rest_request(
    method: str,
    table: str,
    *,
    query: dict[str, str] | None = None,
    payload: Any | None = None,
    prefer: str | None = None,
) -> Any:
    if not SUPABASE_REST_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing in Backend/.env")

    query = query or {}
    url = f"{SUPABASE_REST_URL}/{table}"
    if query:
        url = f"{url}?{parse.urlencode(query, safe='.,:*()')}"

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer

    data = None
    if payload is not None:
        data = json.dumps(payload, default=str).encode("utf-8")

    req = request.Request(url, method=method.upper(), data=data, headers=headers)
    try:
        with request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Supabase {method} {table} failed: {exc.code} {body}") from exc


def chunked(items: list[dict[str, Any]], size: int = 200):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def nan_to_none(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def label(prob: float) -> str:
    if prob >= 0.7:
        return "High"
    if prob >= 0.4:
        return "Medium"
    return "Low"


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def start_pipeline_run() -> str:
    run_id = str(uuid4())
    rest_request(
        "POST",
        "pipeline_runs",
        payload={
            "id": run_id,
            "status": "running",
            "triggered_by": "manual_ingest_script",
            "started_at": datetime.utcnow().isoformat() + "Z",
        },
        prefer="return=minimal",
    )
    return run_id


def finish_pipeline_run(run_id: str, status: str, rows_written: int, error_message: str | None = None) -> None:
    rest_request(
        "PATCH",
        "pipeline_runs",
        query={"id": f"eq.{run_id}"},
        payload={
            "status": status,
            "rows_written": rows_written,
            "error_message": error_message,
            "finished_at": datetime.utcnow().isoformat() + "Z",
        },
        prefer="return=minimal",
    )


def ingest_facilities() -> tuple[list[dict[str, Any]], int]:
    features = load_csv(PROCESSED / "facility_features_raipur.csv")
    crs = load_csv(PROCESSED / "crs_predictions_raipur_facilities.csv")

    if features.empty:
        raise RuntimeError("processed_outputs/facility_features_raipur.csv not found or empty")

    merged = features.copy()
    if not crs.empty and "facility_id" in crs.columns:
        cols = [
            "facility_id",
            "complete_address",
            "street_address",
            "addr:city",
            "addr:state",
            "addr:postcode",
        ]
        cols = [c for c in cols if c in crs.columns]
        merged = merged.merge(crs[cols], on="facility_id", how="left")

    records: list[dict[str, Any]] = []
    for _, row in merged.iterrows():
        records.append(
            {
                "facility_id": normalize_text(row.get("facility_id")),
                "facility_name": normalize_text(row.get("facility_name")) or "Unknown Facility",
                "facility_type": normalize_text(row.get("facility_type")) or "Hospital",
                "district": normalize_text(row.get("district")),
                "latitude": nan_to_none(row.get("latitude")),
                "longitude": nan_to_none(row.get("longitude")),
                "complete_address": normalize_text(row.get("complete_address")),
                "street_address": normalize_text(row.get("street_address")),
                "city": normalize_text(row.get("addr:city")),
                "state": normalize_text(row.get("addr:state")),
                "postcode": normalize_text(row.get("addr:postcode")),
            }
        )

    records = [r for r in records if r.get("facility_id")]
    for batch in chunked(records):
        rest_request(
            "POST",
            "facilities",
            query={"on_conflict": "facility_id"},
            payload=batch,
            prefer="resolution=merge-duplicates,return=minimal",
        )

    return records, len(records)


def ingest_predictions(facility_records: list[dict[str, Any]], run_id: str) -> int:
    features = load_csv(PROCESSED / "facility_features_raipur.csv")
    outage24 = load_csv(PROCESSED / "raipur_facility_outage_risk_24h.csv")
    outage7 = load_csv(PROCESSED / "raipur_facility_outage_risk_7d.csv")

    merged = features.copy()
    if not outage24.empty and "facility_id" in outage24.columns:
        cols = ["facility_id", "pred_outage_prob_24h", "priority_score", "predicted_risk_label"]
        cols = [c for c in cols if c in outage24.columns]
        merged = merged.merge(outage24[cols], on="facility_id", how="left", suffixes=("", "_out24"))

    if not outage7.empty and "facility_id" in outage7.columns:
        cols = ["facility_id", "pred_outage_prob_7d"]
        cols = [c for c in cols if c in outage7.columns]
        merged = merged.merge(outage7[cols], on="facility_id", how="left", suffixes=("", "_out7"))

    valid_ids = {r["facility_id"] for r in facility_records if r.get("facility_id")}
    rows: list[dict[str, Any]] = []

    for _, row in merged.iterrows():
        facility_id = normalize_text(row.get("facility_id"))
        if not facility_id or facility_id not in valid_ids:
            continue

        water_avail = float(nan_to_none(row.get("water_availability")) or 0.5)
        flood_safety = float(nan_to_none(row.get("flood_safety")) or 0.5)
        rainfall_stab = float(nan_to_none(row.get("rainfall_stability")) or 0.5)
        elec_rel = float(nan_to_none(row.get("electricity_reliability")) or 0.5)

        flood_prob = float(nan_to_none(row.get("flood_risk_prob")) or (1.0 - flood_safety))
        water_prob = float(nan_to_none(row.get("water_shortage_risk_prob")) or (1.0 - water_avail))
        power_prob = float(nan_to_none(row.get("power_outage_risk_prob")) or (1.0 - elec_rel))
        sanitation_prob = float(
            nan_to_none(row.get("sanitation_failure_risk_prob"))
            or max(0.0, 1.0 - (rainfall_stab * 0.6 + water_avail * 0.4))
        )

        risk_map = {
            "flood_risk": flood_prob,
            "water_shortage": water_prob,
            "power_outage": power_prob,
            "sanitation_failure": sanitation_prob,
        }
        top_risk_type = max(risk_map, key=risk_map.get)
        top_risk_score = float(risk_map[top_risk_type])

        pred24 = float(nan_to_none(row.get("pred_outage_prob_24h")) or 0.5)
        pred7 = float(nan_to_none(row.get("pred_outage_prob_7d")) or (pred24 * 0.85))
        risk_level = normalize_text(row.get("risk_level")) or label(top_risk_score)
        alert_flag = risk_level == "High" or top_risk_score >= 0.7
        if risk_level == "High" and top_risk_score >= 0.7:
            alert_level = "Critical"
        elif alert_flag:
            alert_level = "High"
        else:
            alert_level = "Normal"

        prediction_ts = normalize_text(row.get("last_updated"))
        if not prediction_ts:
            prediction_ts = datetime.utcnow().isoformat() + "Z"

        rows.append(
            {
                "facility_id": facility_id,
                "prediction_ts": prediction_ts,
                "crs": nan_to_none(row.get("crs")),
                "risk_level": risk_level,
                "gwl_value": nan_to_none(row.get("gwl_value")),
                "rainfall_value": nan_to_none(row.get("rainfall_value")),
                "river_level_value": nan_to_none(row.get("river_level_value")),
                "outage_risk": nan_to_none(row.get("outage_risk")),
                "pred_outage_prob_24h": pred24,
                "pred_outage_prob_7d": pred7,
                "water_availability": water_avail,
                "flood_safety": flood_safety,
                "rainfall_stability": rainfall_stab,
                "electricity_reliability": elec_rel,
                "flood_risk_prob": flood_prob,
                "water_shortage_risk_prob": water_prob,
                "power_outage_risk_prob": power_prob,
                "sanitation_failure_risk_prob": sanitation_prob,
                "flood_risk_label": label(flood_prob),
                "water_shortage_risk_label": label(water_prob),
                "power_outage_risk_label": label(power_prob),
                "sanitation_failure_risk_label": label(sanitation_prob),
                "top_risk_type": top_risk_type,
                "top_risk_score": top_risk_score,
                "alert_flag": alert_flag,
                "alert_level": alert_level,
                "source_run_id": run_id,
            }
        )

    for batch in chunked(rows):
        rest_request(
            "POST",
            "facility_risk_predictions",
            payload=batch,
            prefer="return=minimal",
        )

    return len(rows)


def ingest_climate_trends() -> int:
    env = load_csv(PROCESSED / "environmental_daily_raipur.csv")
    if env.empty:
        return 0

    if "date" not in env.columns:
        return 0

    val_col = "mean_value" if "mean_value" in env.columns else "value"
    if val_col not in env.columns or "metric" not in env.columns:
        return 0

    df = env.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "metric"])
    if df.empty:
        return 0

    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    grouped = df.groupby(["metric", "month"], as_index=False)[val_col].mean()

    rows = [
        {
            "metric": str(r["metric"]),
            "month": r["month"].date().isoformat(),
            "value": float(r[val_col]),
        }
        for _, r in grouped.iterrows()
    ]

    for batch in chunked(rows):
        rest_request(
            "POST",
            "climate_trends_monthly",
            query={"on_conflict": "metric,month"},
            payload=batch,
            prefer="resolution=merge-duplicates,return=minimal",
        )

    return len(rows)


def ingest_alerts() -> int:
    risk_rows = rest_request(
        "GET",
        "v_latest_facility_risk",
        query={
            "select": "facility_id,alert_flag,alert_level,top_risk_type,top_risk_score",
            "alert_flag": "eq.true",
        },
    )
    if not isinstance(risk_rows, list):
        return 0

    facility_rows = rest_request(
        "GET",
        "facilities",
        query={"select": "facility_id,facility_name,facility_type"},
    )
    facilities_by_id = {
        r.get("facility_id"): r for r in facility_rows if isinstance(r, dict) and r.get("facility_id")
    }

    # Clear currently open alerts before recreating current state.
    rest_request(
        "DELETE",
        "alerts",
        query={"status": "eq.open"},
        prefer="return=minimal",
    )

    risk_descriptions = {
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

    rows: list[dict[str, Any]] = []
    for risk in risk_rows:
        if not isinstance(risk, dict):
            continue
        facility_id = risk.get("facility_id")
        if not facility_id:
            continue

        risk_type = str(risk.get("top_risk_type") or "flood_risk")
        desc = risk_descriptions.get(risk_type, risk_descriptions["flood_risk"])

        rows.append(
            {
                "facility_id": facility_id,
                "risk_level": str(risk.get("alert_level") or "High"),
                "top_risk_type": risk_type,
                "top_risk_score": nan_to_none(risk.get("top_risk_score")),
                "predicted_issue": desc["issue"],
                "recommended_action": desc["action"],
                "status": "open",
            }
        )

    if rows:
        for batch in chunked(rows):
            rest_request("POST", "alerts", payload=batch, prefer="return=minimal")

    return len(rows)


def ingest_weather_snapshots() -> int:
    files = sorted(glob.glob(str(PROCESSED / "weather_snapshot_*.json")))
    if not files:
        return 0

    latest = files[-1]
    with open(latest, "r", encoding="utf-8") as f:
        payload = json.load(f)

    active_provider = payload.get("active_weather_provider", "weather_snapshot")
    city = None
    fetched_at = None

    try:
        current = ((payload.get("weather_active") or {}).get("current_weather") or {})
        fetched_at = current.get("fetched_at_utc")
        city = (((current.get("payload") or {}).get("name")))
    except Exception:
        pass

    row = {
        "provider": str(active_provider),
        "city": city or "Raipur",
        "fetched_at": fetched_at,
        "payload": payload,
    }

    rest_request("POST", "weather_snapshots", payload=[row], prefer="return=minimal")
    return 1


def main() -> None:
    total_written = 0
    run_id = start_pipeline_run()
    print(f"[ingest] pipeline_run_id={run_id}")

    try:
        facilities, n_facilities = ingest_facilities()
        total_written += n_facilities
        print(f"[ingest] facilities upserted: {n_facilities}")

        n_predictions = ingest_predictions(facilities, run_id)
        total_written += n_predictions
        print(f"[ingest] risk predictions inserted: {n_predictions}")

        n_climate = ingest_climate_trends()
        total_written += n_climate
        print(f"[ingest] climate trends upserted: {n_climate}")

        n_alerts = ingest_alerts()
        total_written += n_alerts
        print(f"[ingest] alerts refreshed: {n_alerts}")

        n_weather = ingest_weather_snapshots()
        total_written += n_weather
        print(f"[ingest] weather snapshots inserted: {n_weather}")

        finish_pipeline_run(run_id, "success", total_written)
        print(f"[ingest] completed successfully. rows_written={total_written}")
    except Exception as exc:
        finish_pipeline_run(run_id, "failed", total_written, str(exc))
        print(f"[ingest] failed after rows_written={total_written}")
        raise


if __name__ == "__main__":
    main()
