from __future__ import annotations

import httpx
from typing import Any, Dict, List, Optional
from app.weather.gateway import WeatherGateway
from app.weather.models import Location, WeatherState

gateway = WeatherGateway()


def resolve_location_tool(city_name: str) -> Dict[str, Any]:
    """Resolves city name to latitude/longitude coordinates via Open-Meteo geocoding."""
    loc, err = gateway.resolve_location(city_name)
    if not loc or err:
        return {"error": err or f"Could not find coordinates for '{city_name}'"}
    return {
        "name": loc.name,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "country": loc.country,
        "timezone": loc.timezone,
    }


def get_current_weather_tool(latitude: float, longitude: float) -> Dict[str, Any]:
    """Fetches verified live weather metrics for specific coordinates."""
    dummy_loc = Location(name="target_coords", latitude=latitude, longitude=longitude)
    weather, status, reason = gateway.get_weather(dummy_loc)
    if not weather:
        return {"error": reason, "status": status.value}
    return {
        "status": status.value,
        "metrics": weather.model_dump(),
    }


def get_hourly_weather_tool(latitude: float, longitude: float, hours: int = 24) -> Dict[str, Any]:
    """Fetches hourly forecast metrics up to specified hour limit."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,precipitation_probability,precipitation,wind_speed_10m",
        "forecast_days": 2,
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])[:hours]
            temps = hourly.get("temperature_2m", [])[:hours]
            precips = hourly.get("precipitation", [])[:hours]
            winds = hourly.get("wind_speed_10m", [])[:hours]

            return {
                "count": len(times),
                "times": times,
                "temperatures": temps,
                "precipitations": precips,
                "wind_speeds": winds,
            }
    except Exception as e:
        return {"error": f"Failed to fetch hourly weather: {e}"}


def get_daily_weather_tool(latitude: float, longitude: float, days: int = 7) -> Dict[str, Any]:
    """Fetches daily summary weather metrics (max/min temps, precipitation sum)."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
        "forecast_days": min(days, 14),
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return {"daily": data.get("daily", {})}
    except Exception as e:
        return {"error": f"Failed to fetch daily weather: {e}"}


def compare_weather_tool(latitude: float, longitude: float) -> Dict[str, Any]:
    """Compares current weather metrics against today's forecast extremes."""
    curr = get_current_weather_tool(latitude, longitude)
    daily = get_daily_weather_tool(latitude, longitude, days=1)

    if "error" in curr or "error" in daily:
        return {"error": "Could not compile weather comparison."}

    metrics = curr.get("metrics", {})
    daily_data = daily.get("daily", {})

    max_temp = (daily_data.get("temperature_2m_max") or [None])[0]
    min_temp = (daily_data.get("temperature_2m_min") or [None])[0]
    max_wind = (daily_data.get("wind_speed_10m_max") or [None])[0]
    curr_temp = metrics.get("temperature_2m")
    curr_wind = metrics.get("wind_speed_10m")

    return {
        "current_temperature": curr_temp,
        "daily_min_temperature": min_temp,
        "daily_max_temperature": max_temp,
        "current_wind_speed": curr_wind,
        "daily_max_wind_speed": max_wind,
        "is_near_peak_wind": (curr_wind >= max_wind * 0.9) if (curr_wind and max_wind) else False,
    }
