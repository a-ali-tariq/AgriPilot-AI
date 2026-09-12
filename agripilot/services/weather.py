"""Weather lookup with a clearly labelled mock fallback (PRD §9, §10).

Never raises. If anything goes wrong — no API key, network error, bad payload —
it returns mock data with `source="mock"` so the UI can say so plainly.
"""
from __future__ import annotations

import logging
import re

from .. import catalog
from ..config import get_secret
from ..models import Farm, WeatherSummary

log = logging.getLogger(__name__)

OWM_CURRENT = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST = "https://api.openweathermap.org/data/2.5/forecast"
TIMEOUT_S = 8


def _redact(message: str) -> str:
    """Strip any appid=... from a message before it reaches a log.

    OpenWeatherMap passes the key as a query parameter, and requests puts the
    full URL into its exception text — so an unredacted log line would leak the
    key (PRD §9: keys must never be exposed).
    """
    return re.sub(r"(appid=)[^&\s]+", r"\1<redacted>", message)


def _mock(farm: Farm, reason: str = "") -> WeatherSummary:
    data = catalog.mock_weather(farm.province)
    if reason:
        log.info("Using mock weather for %s: %s", farm.province, _redact(reason))
    return WeatherSummary(
        avg_temp=float(data["avg_temp"]),
        max_temp=float(data["max_temp"]),
        min_temp=float(data["min_temp"]),
        rainfall_mm_30d=float(data["rainfall_mm_30d"]),
        forecast_rain_mm_7d=float(data["forecast_rain_mm_7d"]),
        humidity_pct=float(data.get("humidity_pct", 50)),
        source="mock",
        location_label=f"{farm.district}, {farm.province}",
    )


def get(farm: Farm) -> WeatherSummary:
    """Live weather for the farm's district, or mock data if unavailable."""
    api_key = get_secret("OPENWEATHER_API_KEY")
    if not api_key:
        return _mock(farm, "no OPENWEATHER_API_KEY configured")

    coords = (farm.lat, farm.lon) if farm.lat and farm.lon else catalog.district_coords(
        farm.province, farm.district
    )
    if not coords:
        return _mock(farm, f"no coordinates for {farm.district}")

    lat, lon = coords
    try:
        import requests

        params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
        current = requests.get(OWM_CURRENT, params=params, timeout=TIMEOUT_S)
        current.raise_for_status()
        cur = current.json()

        forecast = requests.get(OWM_FORECAST, params=params, timeout=TIMEOUT_S)
        forecast.raise_for_status()
        entries = forecast.json().get("list", [])

        temps = [e["main"]["temp"] for e in entries if "main" in e]
        rain_5d = sum(e.get("rain", {}).get("3h", 0.0) for e in entries)

        main = cur.get("main", {})
        avg = sum(temps) / len(temps) if temps else float(main.get("temp", 25))
        # OWM's free tier gives 5 days; scale to a 7-day figure and estimate the
        # trailing 30 days from it, both clearly derived rather than observed.
        forecast_7d = rain_5d * (7 / 5)
        return WeatherSummary(
            avg_temp=round(avg, 1),
            max_temp=round(max([main.get("temp_max", avg)] + temps), 1),
            min_temp=round(min([main.get("temp_min", avg)] + temps), 1),
            rainfall_mm_30d=round(rain_5d * 6, 1),
            forecast_rain_mm_7d=round(forecast_7d, 1),
            humidity_pct=float(main.get("humidity", 50)),
            source="live",
            location_label=f"{farm.district}, {farm.province}",
        )
    except Exception as exc:  # network, HTTP, schema — all fall back identically
        return _mock(farm, f"{type(exc).__name__}: {exc}")


def source_label(weather: WeatherSummary) -> str:
    if weather.source == "live":
        return f"Weather: live — OpenWeatherMap, {weather.location_label}"
    return (
        "Weather: demo data — live weather source unavailable. "
        f"Showing typical seasonal values for {weather.location_label}."
    )
