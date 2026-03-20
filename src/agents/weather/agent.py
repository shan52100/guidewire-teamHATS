"""Weather data ingestion agent.

Fetches real-time weather data from OpenWeatherMap API and derives
disruption events for parametric insurance triggers.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from loguru import logger

from src.config.settings import settings
from src.models.schemas import (
    AgentState,
    DisruptionEvent,
    DisruptionType,
    WeatherData,
)

# ── Constants ────────────────────────────────────────────────────────────────

OPENWEATHERMAP_URL = "https://api.openweathermap.org/data/2.5/weather"
AIR_POLLUTION_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

# Disruption thresholds (aligned with settings where available)
HEAVY_RAIN_THRESHOLD_MM: float = settings.heavy_rain_mm       # 20 mm
FLOOD_ALERT_LEVEL: int = settings.flood_alert_level            # 3
POLLUTION_AQI_THRESHOLD: int = settings.pollution_aqi_threshold  # 300
HIGH_WIND_THRESHOLD_KPH: float = 50.0
LOW_VISIBILITY_THRESHOLD_KM: float = 1.0


# ── API helpers ──────────────────────────────────────────────────────────────

async def fetch_weather_data(
    latitude: float,
    longitude: float,
    zone_id: str,
    api_key: str | None = None,
) -> WeatherData:
    """Fetch current weather from OpenWeatherMap and return a WeatherData model.

    Falls back to a synthetic default when the API key is missing or the
    request fails, so the pipeline never hard-crashes on external I/O.
    """
    api_key = api_key or settings.weather_api_key

    if not api_key:
        logger.warning("No WEATHER_API_KEY configured – returning synthetic weather data")
        return _synthetic_weather(zone_id)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # ── Current weather ──────────────────────────────────────────
            weather_resp = await client.get(
                OPENWEATHERMAP_URL,
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "appid": api_key,
                    "units": "metric",
                },
            )
            weather_resp.raise_for_status()
            weather_json: dict[str, Any] = weather_resp.json()

            # ── Air quality (best-effort) ────────────────────────────────
            aqi: int | None = None
            try:
                aqi_resp = await client.get(
                    AIR_POLLUTION_URL,
                    params={
                        "lat": latitude,
                        "lon": longitude,
                        "appid": api_key,
                    },
                )
                aqi_resp.raise_for_status()
                aqi_json = aqi_resp.json()
                # OWM returns AQI 1-5; we scale to approximate real AQI
                raw_aqi: int = aqi_json["list"][0]["main"]["aqi"]
                aqi = _scale_aqi(raw_aqi)
            except Exception:
                logger.debug("AQI fetch failed – continuing without pollution data")

        return _parse_weather_response(weather_json, zone_id, aqi)

    except httpx.HTTPStatusError as exc:
        logger.error(f"OpenWeatherMap HTTP error {exc.response.status_code}: {exc}")
        return _synthetic_weather(zone_id)
    except httpx.RequestError as exc:
        logger.error(f"OpenWeatherMap request error: {exc}")
        return _synthetic_weather(zone_id)


# ── Parsing helpers ──────────────────────────────────────────────────────────

def _parse_weather_response(
    data: dict[str, Any],
    zone_id: str,
    aqi: int | None,
) -> WeatherData:
    """Transform raw OWM JSON into our domain model."""
    main = data.get("main", {})
    wind = data.get("wind", {})
    rain = data.get("rain", {})
    weather_desc: str = data.get("weather", [{}])[0].get("main", "Clear")
    visibility_m: float = data.get("visibility", 10000)

    rainfall_mm = rain.get("1h", 0.0) or rain.get("3h", 0.0)

    # Determine flood alert level heuristic
    flood_level = 0
    if rainfall_mm >= HEAVY_RAIN_THRESHOLD_MM * 3:
        flood_level = 4
    elif rainfall_mm >= HEAVY_RAIN_THRESHOLD_MM * 2:
        flood_level = 3
    elif rainfall_mm >= HEAVY_RAIN_THRESHOLD_MM:
        flood_level = 2
    elif rainfall_mm >= HEAVY_RAIN_THRESHOLD_MM * 0.5:
        flood_level = 1

    return WeatherData(
        zone_id=zone_id,
        timestamp=datetime.now(tz=timezone.utc),
        temperature=main.get("temp", 25.0),
        humidity=main.get("humidity", 50.0),
        rainfall_mm=rainfall_mm,
        wind_speed=wind.get("speed", 0.0) * 3.6,  # m/s → km/h
        aqi=aqi,
        flood_alert_level=flood_level,
        visibility_km=round(visibility_m / 1000, 2),
        condition=weather_desc.lower(),
    )


def _scale_aqi(owm_aqi: int) -> int:
    """Map OWM 1-5 scale to approximate real AQI value."""
    mapping = {1: 25, 2: 75, 3: 150, 4: 250, 5: 400}
    return mapping.get(owm_aqi, 100)


def _synthetic_weather(zone_id: str) -> WeatherData:
    """Return benign synthetic weather for fallback / testing."""
    return WeatherData(
        zone_id=zone_id,
        timestamp=datetime.now(tz=timezone.utc),
        temperature=30.0,
        humidity=65.0,
        rainfall_mm=0.0,
        wind_speed=10.0,
        aqi=None,
        flood_alert_level=0,
        visibility_km=10.0,
        condition="clear",
    )


# ── Disruption derivation ───────────────────────────────────────────────────

def derive_disruption(weather: WeatherData) -> DisruptionEvent | None:
    """Evaluate weather data against thresholds and create a DisruptionEvent
    if a parametric trigger is met.  Returns ``None`` when conditions are
    within normal limits.
    """
    triggers: list[tuple[DisruptionType, float]] = []

    # Heavy rain
    if weather.rainfall_mm >= HEAVY_RAIN_THRESHOLD_MM:
        severity = min(weather.rainfall_mm / (HEAVY_RAIN_THRESHOLD_MM * 3), 1.0)
        triggers.append((DisruptionType.HEAVY_RAIN, severity))

    # Flood
    if weather.flood_alert_level >= FLOOD_ALERT_LEVEL:
        severity = min(weather.flood_alert_level / 5.0, 1.0)
        triggers.append((DisruptionType.FLOOD, severity))

    # Air pollution
    if weather.aqi is not None and weather.aqi >= POLLUTION_AQI_THRESHOLD:
        severity = min(weather.aqi / 500.0, 1.0)
        triggers.append((DisruptionType.POLLUTION, severity))

    if not triggers:
        return None

    # Pick the most severe single trigger – or flag as multi-trigger
    if len(triggers) >= 2:
        max_severity = max(s for _, s in triggers)
        disruption_type = DisruptionType.MULTI_TRIGGER
    else:
        disruption_type, max_severity = triggers[0]

    return DisruptionEvent(
        event_id=f"evt-{uuid4().hex[:12]}",
        zone_id=weather.zone_id,
        disruption_type=disruption_type,
        severity=round(max_severity, 3),
        start_time=weather.timestamp,
        weather_data=weather,
        is_active=True,
    )


# ── LangGraph node ──────────────────────────────────────────────────────────

async def weather_agent(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: data_ingestion.

    Expects ``state["zone"]`` (or falls back to ``state["claim"].location``)
    to determine coordinates.  Populates ``state["weather"]`` and optionally
    ``state["disruption"]``.
    """
    logger.info("Weather agent: starting data ingestion")

    try:
        # Resolve coordinates
        zone = state.get("zone")
        claim = state.get("claim")

        if zone is not None:
            lat = zone.center.latitude if hasattr(zone, "center") else zone["center"]["latitude"]
            lon = zone.center.longitude if hasattr(zone, "center") else zone["center"]["longitude"]
            zone_id = zone.zone_id if hasattr(zone, "zone_id") else zone["zone_id"]
        elif claim is not None:
            loc = claim.location if hasattr(claim, "location") else claim["location"]
            lat = loc.latitude if hasattr(loc, "latitude") else loc["latitude"]
            lon = loc.longitude if hasattr(loc, "longitude") else loc["longitude"]
            zone_id = "unknown"
        else:
            logger.warning("Weather agent: no zone or claim location available")
            return {
                **state,
                "reasoning": state.get("reasoning", []) + ["Weather agent: no location data available"],
            }

        # Fetch weather
        weather = await fetch_weather_data(lat, lon, zone_id)
        logger.info(
            f"Weather agent: zone={zone_id} rainfall={weather.rainfall_mm}mm "
            f"aqi={weather.aqi} flood_level={weather.flood_alert_level}"
        )

        # Derive disruption
        disruption = derive_disruption(weather)
        reasoning = state.get("reasoning", []).copy()

        if disruption is not None:
            logger.info(
                f"Weather agent: disruption detected – "
                f"type={disruption.disruption_type.value} severity={disruption.severity}"
            )
            reasoning.append(
                f"Disruption detected: {disruption.disruption_type.value} "
                f"(severity {disruption.severity:.2f})"
            )
        else:
            reasoning.append("No disruption detected from weather data")

        return {
            **state,
            "weather": weather,
            "disruption": disruption,
            "reasoning": reasoning,
        }

    except Exception as exc:
        logger.exception("Weather agent failed")
        return {
            **state,
            "error": f"Weather agent error: {exc}",
            "reasoning": state.get("reasoning", []) + [f"Weather agent error: {exc}"],
        }
