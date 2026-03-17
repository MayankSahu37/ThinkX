import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


DEFAULT_OPENWEATHER_API_KEY = ""
DEFAULT_WEATHERSTACK_API_KEY = ""


@dataclass
class WeatherConfig:
    openweather_api_key: str
    weatherstack_api_key: str
    latitude: float = 21.2514
    longitude: float = 81.6296
    city_name: str = "Raipur"
    country_code: str = "IN"
    units: str = "metric"
    output_dir: Path = Path(__file__).resolve().parent


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_config() -> WeatherConfig:
    ow_key = os.getenv("OPENWEATHER_API_KEY", DEFAULT_OPENWEATHER_API_KEY).strip()
    ws_key = os.getenv("WEATHERSTACK_API_KEY", DEFAULT_WEATHERSTACK_API_KEY).strip()
    if not ow_key:
        raise ValueError("Missing OpenWeather API key.")
    if not ws_key:
        raise ValueError("Missing Weatherstack API key.")
    return WeatherConfig(openweather_api_key=ow_key, weatherstack_api_key=ws_key)


def safe_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return {"raw_text": response.text, "status_code": response.status_code}


def fetch_json(url: str, params: dict[str, Any] | None = None, timeout: int = 45) -> dict[str, Any]:
    with requests.get(url, params=params, timeout=timeout) as resp:
        payload = safe_json(resp)
        return {
            "url": resp.url,
            "status_code": resp.status_code,
            "ok": resp.ok,
            "payload": payload,
            "fetched_at_utc": utc_now_iso(),
        }


def fetch_openweather_bundle(cfg: WeatherConfig) -> dict[str, Any]:
    common = {
        "appid": cfg.openweather_api_key,
        "units": cfg.units,
        "lat": cfg.latitude,
        "lon": cfg.longitude,
    }
    current = fetch_json(
        "https://api.openweathermap.org/data/2.5/weather",
        params={**common, "q": f"{cfg.city_name},{cfg.country_code}"},
    )
    forecast_5d = fetch_json("https://api.openweathermap.org/data/2.5/forecast", params=common)
    hourly_48: list[dict[str, Any]] = []
    daily_8: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []

    forecast_payload = forecast_5d.get("payload", {}) if forecast_5d.get("ok") else {}
    forecast_items = forecast_payload.get("list", []) if isinstance(forecast_payload, dict) else []
    if not hourly_48 and forecast_items:
        hourly_48 = forecast_items[:16]
    if not daily_8 and forecast_items:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for rec in forecast_items:
            key = str(rec.get("dt_txt", "")).split(" ")[0]
            grouped.setdefault(key, []).append(rec)
        daily_8 = []
        for day, items in list(grouped.items())[:8]:
            temps = [i.get("main", {}).get("temp") for i in items]
            temps = [t for t in temps if isinstance(t, (int, float))]
            daily_8.append(
                {
                    "date": day,
                    "temp_min": min(temps) if temps else None,
                    "temp_max": max(temps) if temps else None,
                    "temp_avg": (sum(temps) / len(temps)) if temps else None,
                    "records": len(items),
                }
            )

    return {
        "meta": {
            "provider": "OpenWeather",
            "city": cfg.city_name,
            "country": cfg.country_code,
            "lat": cfg.latitude,
            "lon": cfg.longitude,
            "units": cfg.units,
            "fetched_at_utc": utc_now_iso(),
        },
        "current_weather": current,
        "forecast_5d_raw": forecast_5d,
        "availability": {
            "current_ok": current.get("ok", False),
            "forecast_5d_ok": forecast_5d.get("ok", False),
        },
        "hourly_48h": {"count": len(hourly_48), "records": hourly_48},
        "daily_8d": {"count": len(daily_8), "records": daily_8},
        "weather_alerts": {"count": len(alerts), "records": alerts},
    }


def fetch_weatherstack_bundle(cfg: WeatherConfig) -> dict[str, Any]:
    query = f"{cfg.city_name},{cfg.country_code}"
    common = {"access_key": cfg.weatherstack_api_key, "query": query}
    current = fetch_json("http://api.weatherstack.com/current", params=common)
    forecast = fetch_json("http://api.weatherstack.com/forecast", params={**common, "forecast_days": 8, "hourly": 1})

    payload = forecast.get("payload", {}) if forecast.get("ok") else {}
    forecast_block = payload.get("forecast", {}) if isinstance(payload, dict) else {}
    daily_8 = []
    hourly_48 = []
    if isinstance(forecast_block, dict):
        for day in sorted(forecast_block.keys())[:8]:
            rec = forecast_block.get(day, {})
            daily_8.append(
                {
                    "date": day,
                    "temp_min": rec.get("mintemp"),
                    "temp_max": rec.get("maxtemp"),
                    "temp_avg": rec.get("avgtemp"),
                    "total_precip": rec.get("totalprecip"),
                }
            )
            for hour in rec.get("hourly", []):
                if len(hourly_48) >= 48:
                    break
                hourly_48.append(
                    {
                        "date": day,
                        "time": hour.get("time"),
                        "temp_c": hour.get("temperature"),
                        "humidity": hour.get("humidity"),
                        "precip": hour.get("precip"),
                    }
                )

    alerts = payload.get("alerts", []) if isinstance(payload, dict) else []
    cp = current.get("payload", {}) if current.get("ok") else {}
    err = str(cp.get("error", "")) if isinstance(cp, dict) and cp.get("success") is False else ""

    return {
        "meta": {
            "provider": "Weatherstack",
            "city": cfg.city_name,
            "country": cfg.country_code,
            "query": query,
            "fetched_at_utc": utc_now_iso(),
        },
        "current_weather": current,
        "forecast_raw": forecast,
        "availability": {
            "current_ok": current.get("ok", False),
            "current_error": err,
            "forecast_ok": forecast.get("ok", False) and isinstance(forecast_block, dict),
        },
        "hourly_48h": {"count": len(hourly_48), "records": hourly_48},
        "daily_8d": {"count": len(daily_8), "records": daily_8},
        "weather_alerts": {"count": len(alerts), "records": alerts if isinstance(alerts, list) else []},
    }


def choose_primary_weather(openweather: dict[str, Any], weatherstack: dict[str, Any]) -> dict[str, Any]:
    ow_av = openweather.get("availability", {})
    ws_av = weatherstack.get("availability", {})
    ow_ok = bool(ow_av.get("current_ok")) and bool(ow_av.get("forecast_5d_ok"))
    ws_ok = bool(ws_av.get("current_ok")) and bool(ws_av.get("forecast_ok"))
    if ow_ok:
        return {"provider": "OpenWeather", "bundle": openweather}
    if ws_ok:
        return {"provider": "Weatherstack", "bundle": weatherstack}
    return {"provider": "OpenWeather", "bundle": openweather}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_weather_snapshot(cfg: WeatherConfig) -> dict[str, Any]:
    openweather = fetch_openweather_bundle(cfg)
    weatherstack = fetch_weatherstack_bundle(cfg)
    primary = choose_primary_weather(openweather, weatherstack)
    return {
        "generated_at_utc": utc_now_iso(),
        "scope": {
            "city": cfg.city_name,
            "country": cfg.country_code,
            "lat": cfg.latitude,
            "lon": cfg.longitude,
        },
        "active_weather_provider": primary["provider"],
        "weather_active": primary["bundle"],
        "openweather": openweather,
        "weatherstack": weatherstack,
    }


def main() -> None:
    cfg = get_config()
    snapshot = build_weather_snapshot(cfg)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    combined_path = cfg.output_dir / f"weather_snapshot_{ts}.json"
    openweather_path = cfg.output_dir / f"openweather_snapshot_{ts}.json"
    weatherstack_path = cfg.output_dir / f"weatherstack_snapshot_{ts}.json"

    write_json(combined_path, snapshot)
    write_json(openweather_path, snapshot["openweather"])
    write_json(weatherstack_path, snapshot["weatherstack"])

    print("Weather integration complete.")
    print(f"- Combined snapshot: {combined_path.name}")
    print(f"- OpenWeather snapshot: {openweather_path.name}")
    print(f"- Weatherstack snapshot: {weatherstack_path.name}")
    print(f"- Active weather provider: {snapshot['active_weather_provider']}")

    ow = snapshot["openweather"]
    print("\nOpenWeather summary:")
    print(f"- Current weather OK: {ow['availability']['current_ok']}")
    print(f"- 5-day forecast OK: {ow['availability']['forecast_5d_ok']}")
    print(f"- Hourly records (up to 48h): {ow['hourly_48h']['count']}")
    print(f"- Daily records (up to 8d): {ow['daily_8d']['count']}")
    print(f"- Alerts count: {ow['weather_alerts']['count']}")

    ws = snapshot["weatherstack"]
    print("\nWeatherstack summary:")
    print(f"- Current weather OK: {ws['availability']['current_ok']}")
    print(f"- Forecast OK: {ws['availability']['forecast_ok']}")
    print(f"- Hourly records (up to 48h): {ws['hourly_48h']['count']}")
    print(f"- Daily records (up to 8d): {ws['daily_8d']['count']}")
    print(f"- Alerts count: {ws['weather_alerts']['count']}")


if __name__ == "__main__":
    main()
