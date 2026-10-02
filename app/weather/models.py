from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class WeatherStatus(str, Enum):
    """Integrity and consensus status of the retrieved weather state."""
    VALID = "valid"
    UNCERTAIN = "uncertain"
    UNAVAILABLE = "unavailable"


class Location(BaseModel):
    """Geocoded geographical entity."""
    name: str
    latitude: float
    longitude: float
    country: Optional[str] = None
    admin1: Optional[str] = None
    timezone: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class WeatherState(BaseModel):
    """
    Standardized weather snapshot containing verified meteorological metrics.
    Corresponds directly to required Open-Meteo fields and SOP evidence fields.
    """
    temperature_2m: Optional[float] = Field(None, description="Air temperature at 2 meters (°C)")
    apparent_temperature: Optional[float] = Field(None, description="Apparent / 'feels like' temperature (°C)")
    relative_humidity_2m: Optional[float] = Field(None, description="Relative humidity at 2 meters (%)")
    precipitation: Optional[float] = Field(None, description="Precipitation rate / amount (mm)")
    precipitation_probability: Optional[float] = Field(None, description="Precipitation probability (0-100%)")
    wind_speed_10m: Optional[float] = Field(None, description="Wind speed at 10 meters (km/h)")
    wind_gusts_10m: Optional[float] = Field(None, description="Wind gusts at 10 meters (km/h)")
    uv_index: Optional[float] = Field(None, description="Ultraviolet index (0-12+)")
    visibility: Optional[float] = Field(None, description="Horizontal visibility in meters")
    weather_code: Optional[int] = Field(None, description="WMO weather interpretation code")
    is_day: Optional[int] = Field(None, description="1 for day, 0 for night")
    timestamp: Optional[str] = Field(None, description="ISO-8601 observation timestamp")
    provider: str = Field(default="open-meteo", description="Meteorological provider source")

    model_config = ConfigDict(extra="ignore")

    def to_context(self) -> Dict[str, Any]:
        """
        Converts the weather state into both nested and flat dictionaries
        for flexible policy engine context matching.
        """
        data = self.model_dump()
        # Provide both flat keys and nested 'weather' dictionary
        context: Dict[str, Any] = {
            "weather": data,
        }
        # Also include standard aliases (e.g. wind_speed alias for wind_speed_10m)
        if self.wind_speed_10m is not None:
            data["wind_speed"] = self.wind_speed_10m
        if self.wind_gusts_10m is not None:
            data["wind_gust"] = self.wind_gusts_10m
            data["wind_gusts"] = self.wind_gusts_10m
        if self.temperature_2m is not None:
            data["temperature"] = self.temperature_2m

        for k, v in data.items():
            context[k] = v

        return context
