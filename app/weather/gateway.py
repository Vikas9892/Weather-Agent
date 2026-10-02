from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from app.weather.models import Location, WeatherState, WeatherStatus
from app.weather.providers.open_meteo import OpenMeteoProvider

logger = logging.getLogger(__name__)


class WeatherGateway:
    """
    Gateway decoupling application and policy engine from specific weather provider APIs.
    Supports primary provider, fallback/mock overrides, and multi-provider consensus checks.
    """

    def __init__(
        self,
        primary_provider: Optional[OpenMeteoProvider] = None,
        secondary_providers: Optional[List[Any]] = None,
    ):
        self.primary = primary_provider or OpenMeteoProvider()
        self.secondaries = secondary_providers or []
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
        Resolves location name to geographical coordinates.
        Returns (Location, error_message).
        """
        if self._simulate_location_failure:
            return None, "Simulated location service failure"

        if self._mock_location is not None:
            return self._mock_location, None

        loc = self.primary.geocode(location_query)
        if loc is None:
            return None, f"Could not resolve location '{location_query}'. Please check the city or region name."
        return loc, None

    def get_weather(self, location: Location) -> Tuple[Optional[WeatherState], WeatherStatus, str]:
        """
        Fetches current weather for the resolved location.
        Returns (WeatherState, WeatherStatus, explanation_reason).
        """
        if self._simulate_weather_failure:
            return None, WeatherStatus.UNAVAILABLE, "Weather provider API is currently unreachable."


        if self._mock_weather is not None:
            return self._mock_weather, WeatherStatus.VALID, "Using injected verified weather state."

        weather = self.primary.fetch_current_weather(location.latitude, location.longitude)
        if weather is None:
            return None, WeatherStatus.UNAVAILABLE, f"Weather data currently unavailable for {location.name}."

        # If secondary providers are registered, compare consensus (Milestone 5.5)
        # Check provider disagreement
        if self.secondaries:
            for sec in self.secondaries:
                try:
                    sec_weather = sec.fetch_current_weather(location.latitude, location.longitude)
                    if sec_weather:
                        is_disagree, reason = self.check_disagreement(weather, sec_weather)
                        if is_disagree:
                            return weather, WeatherStatus.UNCERTAIN, f"Provider consensus conflict: {reason}"
                except Exception as e:
                    logger.warning(f"Secondary provider check failed: {e}")

        return weather, WeatherStatus.VALID, "Live weather retrieved successfully."

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
                return True, f"Temperature discrepancy of {diff:.1f}°C between providers"

        if w1.wind_speed_10m is not None and w2.wind_speed_10m is not None:
            diff = abs(w1.wind_speed_10m - w2.wind_speed_10m)
            if diff > 15.0:
                return True, f"Wind speed discrepancy of {diff:.1f} km/h between providers"

        if w1.precipitation is not None and w2.precipitation is not None:
            diff = abs(w1.precipitation - w2.precipitation)
            if diff > 10.0:
                return True, f"Precipitation discrepancy of {diff:.1f} mm between providers"

        return False, "Consistent"
