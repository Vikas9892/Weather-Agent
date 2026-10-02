"""Deterministic replay fixtures for reliable and reproducible evaluations."""
from typing import Any, Dict

REPLAY_FIXTURES: Dict[str, Dict[str, Any]] = {
    "bhopal_severe_monsoon": {
        "location": {"name": "Bhopal", "latitude": 23.25, "longitude": 77.41},
        "weather": {
            "temperature_2m": 26.5,
            "apparent_temperature": 29.0,
            "wind_speed_10m": 28.0,
            "wind_gusts_10m": 52.0,
            "precipitation": 34.0,
            "precipitation_probability": 95,
            "weather_code": 65,
        },
    },
    "high_wind_crosswind": {
        "location": {"name": "Chennai", "latitude": 13.08, "longitude": 80.27},
        "weather": {
            "temperature_2m": 31.0,
            "apparent_temperature": 34.0,
            "wind_speed_10m": 42.0,
            "wind_gusts_10m": 48.0,
            "precipitation": 0.0,
            "precipitation_probability": 10,
            "weather_code": 1,
        },
    },
    "squally_coastal_gale": {
        "location": {"name": "Kanyakumari", "latitude": 8.08, "longitude": 77.55},
        "weather": {
            "temperature_2m": 29.0,
            "apparent_temperature": 32.0,
            "wind_speed_10m": 48.0,
            "wind_gusts_10m": 68.0,
            "precipitation": 5.0,
            "weather_code": 61,
        },
    },
    "extreme_heatwave_delhi": {
        "location": {"name": "Delhi", "latitude": 28.61, "longitude": 77.20},
        "weather": {
            "temperature_2m": 43.5,
            "apparent_temperature": 47.0,
            "relative_humidity_2m": 35.0,
            "wind_speed_10m": 12.0,
            "precipitation": 0.0,
            "uv_index": 9.5,
            "weather_code": 0,
        },
    },
    "severe_thunderstorm": {
        "location": {"name": "Kolkata", "latitude": 22.57, "longitude": 88.36},
        "weather": {
            "temperature_2m": 27.0,
            "wind_speed_10m": 35.0,
            "wind_gusts_10m": 58.0,
            "precipitation": 8.0,
            "precipitation_probability": 90,
            "weather_code": 95,
        },
    },

    "dense_highway_fog": {
        "location": {"name": "Agra", "latitude": 27.18, "longitude": 78.00},
        "weather": {
            "temperature_2m": 11.0,
            "relative_humidity_2m": 96.0,
            "wind_speed_10m": 5.0,
            "visibility": 350.0,
            "weather_code": 45,
            "precipitation": 0.0,
        },
    },
    "ideal_pleasant_picnic": {
        "location": {"name": "Bengaluru", "latitude": 12.97, "longitude": 77.59},
        "weather": {
            "temperature_2m": 23.0,
            "apparent_temperature": 23.0,
            "relative_humidity_2m": 55.0,
            "wind_speed_10m": 12.0,
            "wind_gusts_10m": 15.0,
            "precipitation": 0.0,
            "precipitation_probability": 5,
            "uv_index": 4.0,
            "weather_code": 1,
        },
    },
    "damp_picnic_drizzle": {
        "location": {"name": "Shillong", "latitude": 25.57, "longitude": 91.88},
        "weather": {
            "temperature_2m": 17.0,
            "precipitation": 2.2,
            "precipitation_probability": 75,
            "wind_speed_10m": 15.0,
            "weather_code": 51,
        },
    },
    "freezing_wind_chill": {
        "location": {"name": "Shimla", "latitude": 31.10, "longitude": 77.17},
        "weather": {
            "temperature_2m": 1.0,
            "wind_speed_10m": 26.0,
            "precipitation": 0.0,
            "weather_code": 2,
        },
    },
    "alpine_subzero_hiking": {
        "location": {"name": "Manali", "latitude": 32.24, "longitude": 77.19},
        "weather": {
            "temperature_2m": -3.5,
            "wind_speed_10m": 22.0,
            "precipitation": 1.0,
            "weather_code": 71,
        },
    },
    "playground_wet_burn_hazard": {
        "location": {"name": "Jaipur", "latitude": 26.91, "longitude": 75.78},
        "weather": {
            "temperature_2m": 34.0,
            "uv_index": 8.5,
            "precipitation": 0.0,
            "wind_speed_10m": 10.0,
            "weather_code": 0,
        },
    },
    "missing_evidence_dataset": {
        "location": {"name": "Indore", "latitude": 22.71, "longitude": 75.85},
        # Deliberately missing wind_speed and precipitation
        "weather": {
            "temperature_2m": 25.0,
        },
    },
}
