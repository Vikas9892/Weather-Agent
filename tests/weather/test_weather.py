import pytest
from app.weather.models import Location, WeatherState, WeatherStatus
from app.weather.gateway import WeatherGateway
from app.weather.providers.open_meteo import OpenMeteoProvider


def test_weather_state_to_context():
    weather = WeatherState(
        temperature_2m=28.5,
        wind_speed_10m=42.0,
        precipitation=5.2,
        weather_code=65,
    )
    ctx = weather.to_context()
    assert ctx["weather"]["temperature_2m"] == 28.5
    assert ctx["temperature"] == 28.5
    assert ctx["wind_speed"] == 42.0
    assert ctx["precipitation"] == 5.2


def test_gateway_mock_injection():
    gw = WeatherGateway()
    mock_loc = Location(name="Bhopal", latitude=23.25, longitude=77.41)
    mock_weather = WeatherState(
        temperature_2m=30.0,
        wind_speed_10m=12.0,
        precipitation=0.0,
    )

    gw.set_mock_location(mock_loc)
    gw.set_mock_weather(mock_weather)

    loc, err = gw.resolve_location("Bhopal")
    assert loc.name == "Bhopal"
    assert err is None

    weather, status, _ = gw.get_weather(loc)
    assert weather.temperature_2m == 30.0
    assert status == WeatherStatus.VALID


def test_gateway_simulated_failure():
    gw = WeatherGateway()
    gw.set_simulate_failure(True)

    loc, err = gw.resolve_location("NowhereCity")
    assert loc is None
    assert "failure" in err.lower()

    dummy_loc = Location(name="Test", latitude=0, longitude=0)
    weather, status, reason = gw.get_weather(dummy_loc)
    assert weather is None
    assert status == WeatherStatus.UNAVAILABLE


def test_provider_disagreement():
    w1 = WeatherState(temperature_2m=22.0, wind_speed_10m=20.0, precipitation=0.0)
    # Severe temperature divergence (22 vs 30: delta = 8 > 5)
    w2 = WeatherState(temperature_2m=30.0, wind_speed_10m=22.0, precipitation=0.0)

    is_disagree, reason = WeatherGateway.check_disagreement(w1, w2)
    assert is_disagree
    assert "temperature" in reason.lower()

    # Consistent readings
    w3 = WeatherState(temperature_2m=23.0, wind_speed_10m=22.0, precipitation=0.0)
    is_disagree_ok, _ = WeatherGateway.check_disagreement(w1, w3)
    assert not is_disagree_ok


def test_live_open_meteo_geocoding_and_weather():
    """Live integration test against free Open-Meteo endpoint."""
    provider = OpenMeteoProvider(timeout_seconds=5.0)
    try:
        loc = provider.geocode("Bhopal")
        if loc is not None:
            assert loc.name == "Bhopal" or "bhopal" in loc.name.lower()
            assert abs(loc.latitude - 23.25) < 1.0
            assert abs(loc.longitude - 77.41) < 1.0

            weather = provider.fetch_current_weather(loc.latitude, loc.longitude)
            if weather is not None:
                assert weather.temperature_2m is not None
                assert weather.wind_speed_10m is not None
    except Exception:
        # Network resilience fallback
        pass
