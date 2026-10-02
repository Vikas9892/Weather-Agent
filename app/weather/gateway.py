from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.weather.models import Location, WeatherState, WeatherStatus
from app.weather.providers.open_meteo import OpenMeteoProvider
from app.weather.providers.open_weather import OpenWeatherProvider
from app.weather.providers.weather_api import WeatherAPIProvider

logger = logging.getLogger(__name__)


class WeatherGateway:
    """
    Multi-provider weather gateway managing Open-Meteo, OpenWeatherMap, and WeatherAPI.com.
    Executes primary retrieval and multi-provider consensus / disagreement checks.
    """

    def __init__(
        self,
        primary_provider: Optional[OpenMeteoProvider] = None,
        secondary_providers: Optional[List[Any]] = None,
    ):
        self.primary = primary_provider or OpenMeteoProvider()
        # Auto-register OpenWeather and WeatherAPI providers if not explicitly supplied
        if secondary_providers is not None:
            self.secondaries = secondary_providers
        else:
            self.secondaries = [OpenWeatherProvider(), WeatherAPIProvider()]

        self._mock_weather: Optional[WeatherState] = None
        self._mock_location: Optional[Location] = None
        self._simulate_location_failure: bool = False
        self._simulate_weather_failure: bool = False

    def set_mock_weather(self, weather: Optional[WeatherState]) -> None:
        """Injects mock weather state for deterministic evaluation/testing."""
        self._mock_weather = weather

    def set_mock_location(self, location: Optional[Location]) -> None:
        """Injects mock location for testing."""
        self._mock_location = location

    def set_simulate_failure(self, simulate: bool) -> None:
        """Simulates both location and weather API failure."""
        self._simulate_location_failure = simulate
        self._simulate_weather_failure = simulate

    def set_simulate_weather_failure(self, simulate: bool) -> None:
        """Simulates only weather API failure while allowing location resolution."""
        self._simulate_weather_failure = simulate

    def resolve_location(self, location_query: str) -> Tuple[Optional[Location], Optional[str]]:
        """
        Resolves location name to geographical coordinates using available providers.
        Tries Open-Meteo geocoding first, then falls back to OpenWeather or WeatherAPI.
        """
        if self._simulate_location_failure:
            return None, "Simulated location service failure"

        if self._mock_location is not None:
            return self._mock_location, None

        # 1. Primary: Open-Meteo
        loc = self.primary.geocode(location_query)
        if loc:
            return loc, None

        # 2. Fallbacks: OpenWeather & WeatherAPI
        for sec in self.secondaries:
            try:
                if hasattr(sec, "geocode"):
                    fallback_loc = sec.geocode(location_query)
                    if fallback_loc:
                        return fallback_loc, None
            except Exception as e:
                logger.debug(f"Secondary geocode fallback error: {e}")

        return None, f"Could not resolve location '{location_query}'. Please check the city or region name."

    def get_weather(self, location: Location) -> Tuple[Optional[WeatherState], WeatherStatus, str]:
        """
        Fetches current weather for the resolved location.
        Cross-checks secondary providers when available for disagreement detection.
        """
        if self._simulate_weather_failure:
            return None, WeatherStatus.UNAVAILABLE, "Weather provider API is currently unreachable."

        if self._mock_weather is not None:
            return self._mock_weather, WeatherStatus.VALID, "Using injected verified weather state."

        # Fetch primary
        weather = self.primary.fetch_current_weather(location.latitude, location.longitude)
        if weather is None:
            # Try secondary providers if primary failed
            for sec in self.secondaries:
                try:
                    if hasattr(sec, "fetch_current_weather"):
                        sec_weather = sec.fetch_current_weather(location.latitude, location.longitude)
                        if sec_weather:
                            return sec_weather, WeatherStatus.VALID, f"Retrieved via fallback provider {sec_weather.provider}."
                except Exception as e:
                    logger.debug(f"Fallback weather fetch error: {e}")

            return None, WeatherStatus.UNAVAILABLE, f"Weather data currently unavailable for {location.name}."

        # Milestone 5.5: Check multi-provider consensus & disagreement
        if self.secondaries:
            for sec in self.secondaries:
                try:
                    if hasattr(sec, "is_configured") and not sec.is_configured():
                        continue
                    if hasattr(sec, "fetch_current_weather"):
                        sec_weather = sec.fetch_current_weather(location.latitude, location.longitude)
                        if sec_weather:
                            is_disagree, reason = self.check_disagreement(weather, sec_weather)
                            if is_disagree:
                                return weather, WeatherStatus.UNCERTAIN, f"Multi-provider disagreement detected: {reason}"
                except Exception as e:
                    logger.warning(f"Secondary provider disagreement check error: {e}")

        return weather, WeatherStatus.VALID, "Live weather retrieved and verified."

    @staticmethod
    def check_disagreement(w1: WeatherState, w2: WeatherState) -> Tuple[bool, str]:
        """
        Checks for material disagreement between two weather provider readings.
        Thresholds:
        - Temperature difference > 5.0 °C
        - Wind speed difference > 15.0 km/h
        - Precipitation difference > 10.0 mm
        """
        if w1.temperature_2m is not None and w2.temperature_2m is not None:
            diff = abs(w1.temperature_2m - w2.temperature_2m)
            if diff > 5.0:
                return True, f"Temperature discrepancy of {diff:.1f}°C between {w1.provider} and {w2.provider}"

        if w1.wind_speed_10m is not None and w2.wind_speed_10m is not None:
            diff = abs(w1.wind_speed_10m - w2.wind_speed_10m)
            if diff > 15.0:
                return True, f"Wind speed discrepancy of {diff:.1f} km/h between {w1.provider} and {w2.provider}"

        if w1.precipitation is not None and w2.precipitation is not None:
            diff = abs(w1.precipitation - w2.precipitation)
            if diff > 10.0:
                return True, f"Precipitation discrepancy of {diff:.1f} mm between {w1.provider} and {w2.provider}"

        return False, "Consistent"
