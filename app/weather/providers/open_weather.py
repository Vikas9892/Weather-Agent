from __future__ import annotations

import logging
from typing import Optional
import httpx

from app.config import settings
from app.weather.models import Location, WeatherState

logger = logging.getLogger(__name__)


class OpenWeatherProvider:
    """Weather provider for OpenWeatherMap (Current Weather Data API 2.5)."""

    def __init__(self, api_key: Optional[str] = None, timeout_seconds: float = 10.0):
        self.api_key = api_key or settings.OPENWEATHER_API_KEY
        self.timeout = timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("your_") and len(self.api_key) > 5)

    def geocode(self, city_name: str) -> Optional[Location]:
        if not self.is_configured() or not city_name:
            return None
        url = "https://api.openweathermap.org/geo/1.0/direct"
        params = {"q": city_name, "limit": 1, "appid": self.api_key}
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
                        admin1=top.get("state"),
                    )
        except Exception as e:
            logger.warning(f"OpenWeather geocoding error: {e}")
        return None

    def fetch_current_weather(self, latitude: float, longitude: float) -> Optional[WeatherState]:
        if not self.is_configured():
            return None
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": self.api_key,
            "units": "metric",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

                main = data.get("main", {})
                wind = data.get("wind", {})
                rain = data.get("rain", {})
                weather_arr = data.get("weather", [{}])

                # OpenWeather wind is m/s; convert to km/h (* 3.6)
                wind_speed_kmh = wind.get("speed", 0.0) * 3.6 if "speed" in wind else None
                wind_gust_kmh = wind.get("gust", 0.0) * 3.6 if "gust" in wind else None
                rain_1h = rain.get("1h", 0.0) if isinstance(rain, dict) else 0.0

                return WeatherState(
                    temperature_2m=main.get("temp"),
                    apparent_temperature=main.get("feels_like"),
                    relative_humidity_2m=main.get("humidity"),
                    precipitation=float(rain_1h),
                    wind_speed_10m=round(wind_speed_kmh, 1) if wind_speed_kmh is not None else None,
                    wind_gusts_10m=round(wind_gust_kmh, 1) if wind_gust_kmh is not None else None,
                    visibility=float(data.get("visibility")) if data.get("visibility") is not None else None,
                    weather_code=weather_arr[0].get("id") if weather_arr else None,
                    provider="openweathermap",
                )
        except Exception as e:
            logger.warning(f"OpenWeather fetch error: {e}")
            return None
