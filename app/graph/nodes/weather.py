from __future__ import annotations

from typing import Any, Dict
from app.graph.state import SafetyState
from app.weather.gateway import WeatherGateway
from app.weather.models import Location, WeatherState, WeatherStatus


def resolve_location_node(state: SafetyState, gateway: WeatherGateway) -> Dict[str, Any]:
    """Geocodes the target location name using Open-Meteo geocoding."""
    loc_name = state.get("location_query")
    if not loc_name:
        return {
            "location": None,
            "weather_error": "No location specified or identifiable from query.",
        }

    loc, err = gateway.resolve_location(loc_name)
    if not loc or err:
        return {
            "location": None,
            "weather_error": err or f"Could not find coordinates for '{loc_name}'.",
        }

    return {
        "location": loc.model_dump(),
        "weather_error": None,
    }


def fetch_weather_node(state: SafetyState, gateway: WeatherGateway) -> Dict[str, Any]:
    """Retrieves live meteorological metrics for the resolved location."""
    loc_dict = state.get("location")
    if not loc_dict:
        return {
            "weather": None,
            "weather_status": WeatherStatus.UNAVAILABLE.value,
            "weather_error": "Location not resolved.",
        }

    loc = Location.model_validate(loc_dict)
    weather, status, reason = gateway.get_weather(loc)

    if not weather:
        return {
            "weather": None,
            "weather_status": status.value,
            "weather_error": reason,
        }

    return {
        "weather": weather.to_context(),
        "weather_status": status.value,
        "weather_error": None,
    }


def location_fallback_node(state: SafetyState) -> Dict[str, Any]:
    """Honest failure node when a location cannot be resolved."""
    loc_name = state.get("location_query", "the requested area")
    err = state.get("weather_error", "Location could not be verified.")
    response_msg = (
        f"We could not resolve the geographical location '{loc_name}' ({err}). "
        f"Because safety advice requires accurate local weather data, we cannot guess or provide safety recommendations. "
        f"Please provide a recognized city or district name."
    )
    return {
        "response": response_msg,
        "safety_status": "BLOCKED",
        "safety_reason": "Location resolution failure",
    }


def weather_fallback_node(state: SafetyState) -> Dict[str, Any]:
    """Honest failure node when live weather data cannot be fetched."""
    loc_name = state.get("location_query", "your area")
    err = state.get("weather_error", "Weather service unreachable.")
    response_msg = (
        f"Live weather data for {loc_name} is currently unavailable ({err}). "
        f"As an outdoor safety system, we never invent or recall weather figures. "
        f"Please check your local weather service directly before proceeding."
    )
    return {
        "response": response_msg,
        "safety_status": "BLOCKED",
        "safety_reason": "Live weather service failure",
    }
