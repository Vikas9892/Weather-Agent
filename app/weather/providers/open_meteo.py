from __future__ import annotations

import logging
from typing import Optional
import httpx

from app.weather.models import Location, WeatherState

logger = logging.getLogger(__name__)

# Explicit weather metric fields required for SOP evaluation
CURRENT_WEATHER_FIELDS = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "precipitation",
    "precipitation_probability",
    "wind_speed_10m",
    "wind_gusts_10m",
    "uv_index",
    "weather_code",
    "visibility",
    "is_day",
]


class OpenMeteoProvider:
    """Production client for Open-Meteo geocoding and live forecast APIs."""

    def __init__(self, timeout_seconds: float = 10.0, client: Optional[httpx.Client] = None):
        self.timeout = timeout_seconds
        self._client = client

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        return httpx.Client(timeout=self.timeout)

    def geocode(self, city_name: str) -> Optional[Location]:
        """
        Resolves a city name to latitude and longitude using Open-Meteo Geocoding API.
        Returns None if not found or on network failure.
        """
        if not city_name or not city_name.strip():
            return None

        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": city_name.strip(), "count": 5, "format": "json"}

        try:
            client = self._get_client()
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results")
            if not results or len(results) == 0:
                logger.info(f"Geocoding returned 0 results for '{city_name}'")
                return None

            top = results[0]
            return Location(
                name=top.get("name", city_name),
                latitude=float(top["latitude"]),
                longitude=float(top["longitude"]),
                country=top.get("country"),
                admin1=top.get("admin1"),
                timezone=top.get("timezone", "UTC"),
            )
        except Exception as e:
            logger.warning(f"Geocoding failed for '{city_name}': {e}")
            return None

    def fetch_current_weather(self, latitude: float, longitude: float) -> Optional[WeatherState]:
        """
        Fetches current weather snapshot with explicit fields from Open-Meteo forecast API.
        """
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": ",".join(CURRENT_WEATHER_FIELDS),
        }

        try:
            client = self._get_client()
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            current = data.get("current")
            if not current:
                logger.warning(f"Open-Meteo response missing 'current' field for lat={latitude}, lon={longitude}")
                return None

            return WeatherState(
                temperature_2m=current.get("temperature_2m"),
                apparent_temperature=current.get("apparent_temperature"),
                relative_humidity_2m=current.get("relative_humidity_2m"),
                precipitation=current.get("precipitation"),
                precipitation_probability=current.get("precipitation_probability"),
                wind_speed_10m=current.get("wind_speed_10m"),
                wind_gusts_10m=current.get("wind_gusts_10m"),
                uv_index=current.get("uv_index"),
                visibility=current.get("visibility"),
                weather_code=current.get("weather_code"),
                is_day=current.get("is_day"),
                timestamp=current.get("time"),
                provider="open-meteo",
            )
        except Exception as e:
            logger.warning(f"Weather fetch failed for ({latitude}, {longitude}): {e}")
            return None
