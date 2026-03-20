"""Weather service: fetches OpenWeatherMap data, caches results, and detects disruption triggers."""
from __future__ import annotations

import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import httpx
from loguru import logger

from src.config.settings import settings
from src.models.schemas import DisruptionEvent, DisruptionType, WeatherData
from src.utils.helpers import generate_id


class WeatherService:
    """Fetches weather data and detects parametric insurance triggers.

    Supports a *mock mode* that returns synthetic data for demos/testing,
    and a *live mode* that calls the OpenWeatherMap API via ``httpx``.
    Results are cached in-memory with a configurable TTL.
    """

    _CACHE_TTL_SECONDS: int = 300  # 5 minutes

    def __init__(self, mock: bool | None = None) -> None:
        self._mock = mock if mock is not None else settings.mock_weather_api
        self._api_key: str = settings.weather_api_key
        self._base_url: str = "https://api.openweathermap.org/data/2.5"
        self._cache: Dict[str, Tuple[WeatherData, float]] = {}

    # ── Public API ───────────────────────────────────────────────────────────

    async def get_weather(self, lat: float, lon: float, zone_id: str) -> WeatherData:
        """Return current weather for a location, using cache when available."""
        cache_key = f"{zone_id}:{lat:.4f}:{lon:.4f}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            data, ts = cached
            if time.time() - ts < self._CACHE_TTL_SECONDS:
                logger.debug("Weather cache hit for {}", cache_key)
                return data

        data = (
            await self._fetch_mock(zone_id)
            if self._mock
            else await self._fetch_live(lat, lon, zone_id)
        )

        self._cache[cache_key] = (data, time.time())
        logger.info("Weather fetched for zone {} | rain={}mm aqi={}", zone_id, data.rainfall_mm, data.aqi)
        return data

    async def detect_triggers(self, weather: WeatherData) -> List[DisruptionEvent]:
        """Evaluate weather data against parametric thresholds and return any triggered events."""
        events: List[DisruptionEvent] = []
        now = datetime.utcnow()

        # Heavy rain trigger
        if weather.rainfall_mm >= settings.heavy_rain_mm:
            severity = min(weather.rainfall_mm / 100.0, 1.0)
            events.append(
                DisruptionEvent(
                    event_id=generate_id("EVT"),
                    zone_id=weather.zone_id,
                    disruption_type=DisruptionType.HEAVY_RAIN,
                    severity=round(severity, 2),
                    start_time=now,
                    weather_data=weather,
                )
            )

        # Flood trigger
        if weather.flood_alert_level >= settings.flood_alert_level:
            severity = min(weather.flood_alert_level / 5.0, 1.0)
            events.append(
                DisruptionEvent(
                    event_id=generate_id("EVT"),
                    zone_id=weather.zone_id,
                    disruption_type=DisruptionType.FLOOD,
                    severity=round(severity, 2),
                    start_time=now,
                    weather_data=weather,
                )
            )

        # Air quality trigger
        if weather.aqi is not None and weather.aqi >= settings.pollution_aqi_threshold:
            severity = min((weather.aqi - 200) / 300.0, 1.0)
            events.append(
                DisruptionEvent(
                    event_id=generate_id("EVT"),
                    zone_id=weather.zone_id,
                    disruption_type=DisruptionType.POLLUTION,
                    severity=round(severity, 2),
                    start_time=now,
                    weather_data=weather,
                )
            )

        if len(events) > 1:
            # Combine into a single multi-trigger event for scoring
            max_severity = max(e.severity for e in events)
            multi = DisruptionEvent(
                event_id=generate_id("EVT"),
                zone_id=weather.zone_id,
                disruption_type=DisruptionType.MULTI_TRIGGER,
                severity=round(min(max_severity * 1.2, 1.0), 2),
                start_time=now,
                weather_data=weather,
            )
            events.append(multi)

        if events:
            logger.warning(
                "Triggers detected in zone {}: {}",
                weather.zone_id,
                [e.disruption_type.value for e in events],
            )
        return events

    def clear_cache(self) -> None:
        """Flush the in-memory weather cache."""
        self._cache.clear()
        logger.debug("Weather cache cleared")

    # ── Internal ─────────────────────────────────────────────────────────────

    async def _fetch_live(self, lat: float, lon: float, zone_id: str) -> WeatherData:
        """Call OpenWeatherMap current-weather and air-pollution endpoints."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Current weather
            weather_resp = await client.get(
                f"{self._base_url}/weather",
                params={"lat": lat, "lon": lon, "appid": self._api_key, "units": "metric"},
            )
            weather_resp.raise_for_status()
            w = weather_resp.json()

            # Air quality
            aqi: Optional[int] = None
            try:
                aqi_resp = await client.get(
                    f"{self._base_url}/air_pollution",
                    params={"lat": lat, "lon": lon, "appid": self._api_key},
                )
                aqi_resp.raise_for_status()
                aqi_data = aqi_resp.json()
                aqi = aqi_data.get("list", [{}])[0].get("main", {}).get("aqi")
                # OWM returns 1-5 scale; convert to AQI-like range
                if aqi is not None:
                    aqi = aqi * 75  # rough mapping: 5 -> 375
            except Exception:
                logger.warning("Air quality fetch failed; continuing without AQI")

            rain_1h = w.get("rain", {}).get("1h", 0.0)
            condition = w.get("weather", [{}])[0].get("main", "Clear")
            visibility = w.get("visibility", 10000) / 1000.0

            # Derive flood alert from rain + condition
            flood_level = 0
            if rain_1h > 50:
                flood_level = 3
            elif rain_1h > 30:
                flood_level = 2
            elif rain_1h > 15:
                flood_level = 1

            return WeatherData(
                zone_id=zone_id,
                timestamp=datetime.utcnow(),
                temperature=w.get("main", {}).get("temp", 30.0),
                humidity=w.get("main", {}).get("humidity", 70.0),
                rainfall_mm=rain_1h,
                wind_speed=w.get("wind", {}).get("speed", 0.0) * 3.6,  # m/s -> km/h
                aqi=aqi,
                flood_alert_level=flood_level,
                visibility_km=round(visibility, 1),
                condition=condition.lower(),
            )

    async def _fetch_mock(self, zone_id: str) -> WeatherData:
        """Return synthetic weather data for demonstration."""
        # Zone-specific profiles
        profiles: Dict[str, Dict] = {
            "CHN-VLC": {"rain_range": (15, 60), "flood_range": (0, 4), "aqi_range": (100, 350)},
            "CHN-TNG": {"rain_range": (0, 35), "flood_range": (0, 2), "aqi_range": (80, 280)},
            "CHN-ANG": {"rain_range": (0, 15), "flood_range": (0, 1), "aqi_range": (50, 200)},
            "CHN-MYL": {"rain_range": (5, 40), "flood_range": (0, 3), "aqi_range": (90, 320)},
            "CHN-ADR": {"rain_range": (10, 45), "flood_range": (0, 3), "aqi_range": (100, 310)},
        }
        profile = profiles.get(zone_id, {"rain_range": (0, 30), "flood_range": (0, 2), "aqi_range": (50, 250)})

        rainfall = round(random.uniform(*profile["rain_range"]), 1)
        flood = random.randint(*profile["flood_range"])
        aqi_val = random.randint(*profile["aqi_range"])

        conditions = ["clear", "clouds", "rain", "thunderstorm", "drizzle"]
        if rainfall > 30:
            condition = "thunderstorm"
        elif rainfall > 15:
            condition = "rain"
        elif rainfall > 5:
            condition = "drizzle"
        else:
            condition = random.choice(["clear", "clouds"])

        return WeatherData(
            zone_id=zone_id,
            timestamp=datetime.utcnow(),
            temperature=round(random.uniform(24.0, 38.0), 1),
            humidity=round(random.uniform(50.0, 95.0), 1),
            rainfall_mm=rainfall,
            wind_speed=round(random.uniform(5.0, 50.0), 1),
            aqi=aqi_val,
            flood_alert_level=flood,
            visibility_km=round(random.uniform(1.0, 10.0), 1),
            condition=condition,
        )
