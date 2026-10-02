from __future__ import annotations

import logging
from typing import Optional
import httpx

from app.config import settings
from app.weather.models import Location, WeatherState

logger = logging.getLogger(__name__)


class WeatherAPIProvider:
    """Weather provider for WeatherAPI.com (Realtime Weather API)."""

    def __init__(self, api_key: Optional[str] = None, timeout_seconds: float = 10.0):
        self.api_key = api_key or settings.WEATHERAPI_KEY
        self.timeout = timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("your_") and len(self.api_key) > 5)

    def geocode(self, city_name: str) -> Optional[Location]:
        if not self.is_configured() or not city_name:
            return None
        url = "https://api.weatherapi.com/v1/search.json"
        params = {"key": self.api_key, "q": city_name}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                if data and len(data) > 0:
                    top = data[0]
                    return Location(
                        name=top.get("name", city_name),
                        latitude=float(top["lat"]),
                        longitude=float(top["lon"]),
                        country=top.get("country"),
                        admin1=top.get("region"),
                    )
        except Exception as e:
            logger.warning(f"WeatherAPI geocoding error: {e}")
        return None

    def fetch_current_weather(self, latitude: float, longitude: float) -> Optional[WeatherState]:
        if not self.is_configured():
            return None
        url = "https://api.weatherapi.com/v1/current.json"
        params = {
            "key": self.api_key,
            "q": f"{latitude},{longitude}",
            "aqi": "no",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

                current = data.get("current", {})
                if not current:
                    return None

                return WeatherState(
                    temperature_2m=current.get("temp_c"),
                    apparent_temperature=current.get("feelslike_c"),
                    relative_humidity_2m=current.get("humidity"),
                    precipitation=current.get("precip_mm"),
                    wind_speed_10m=current.get("wind_kph"),
                    wind_gusts_10m=current.get("gust_kph"),
                    uv_index=current.get("uv"),
                    visibility=current.get("vis_km", 0.0) * 1000.0 if "vis_km" in current else None,
                    is_day=current.get("is_day"),
                    provider="weatherapi.com",
                )
        except Exception as e:
            logger.warning(f"WeatherAPI fetch error: {e}")
            return None
