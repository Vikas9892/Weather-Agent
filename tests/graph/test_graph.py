import pytest
from app.graph.graph import SafetyAgentGraph
from app.weather.gateway import WeatherGateway
from app.weather.models import Location, WeatherState, WeatherStatus
from app.memory.session import SessionMemoryStore


from app.llm.gateway import LLMGateway


@pytest.fixture
def test_graph():
    gw = WeatherGateway()
    mem = SessionMemoryStore()
    eval_llm = LLMGateway(use_deterministic_only=True)
    return SafetyAgentGraph(weather_gateway=gw, memory=mem, llm_gateway=eval_llm)


def test_graph_success_flow_cycling_wind(test_graph):
    # Set mock weather for Bhopal: Wind (41 km/h) -> triggers CYC-001 (>= 40) but below HAZ-004 (>= 45)
    gw = test_graph.weather_gateway
    gw.set_mock_location(Location(name="Bhopal", latitude=23.25, longitude=77.41))
    gw.set_mock_weather(WeatherState(
        temperature_2m=28.0,
        wind_speed_10m=41.0,
        wind_gusts_10m=44.0,
        precipitation=0.0,
        weather_code=0,
    ))

    result = test_graph.run("Can I go for a bicycle ride in Bhopal today?", session_id="test_s1")

    assert result["selected_sop"] is not None
    assert result["selected_sop"]["id"] == "CYC-001"
    assert "CYC-001" in result["response"]
    assert result["decision_trace"] is not None
    assert result["decision_trace"]["safety_status"] == "APPROVED"


def test_graph_location_failure_branch(test_graph):
    # Simulate location failure
    gw = test_graph.weather_gateway
    gw.set_simulate_failure(True)

    result = test_graph.run("Can I hike in FakeUnrealCityXYZ?", session_id="test_s2")

    assert result["location"] is None
    assert "could not resolve" in result["response"].lower()
    assert result["safety_status"] == "BLOCKED"


def test_graph_weather_failure_branch(test_graph):
    # Location succeeds, but weather fails
    gw = test_graph.weather_gateway
    gw.set_mock_location(Location(name="Bhopal", latitude=23.25, longitude=77.41))
    gw.set_simulate_weather_failure(True)

    result = test_graph.run("Can I jog in Bhopal?", session_id="test_s3")

    assert "unavailable" in result["response"].lower()
    assert result["safety_status"] == "BLOCKED"


def test_graph_no_matching_sop_branch(test_graph):
    # Query an activity for which no SOP exists (e.g. bird photography) in calm weather
    gw = test_graph.weather_gateway
    gw.set_mock_location(Location(name="Bhopal", latitude=23.25, longitude=77.41))
    gw.set_mock_weather(WeatherState(
        temperature_2m=22.0,
        wind_speed_10m=10.0,
        precipitation=0.0,
        weather_code=0,
    ))

    result = test_graph.run("Is it safe to do amateur bird photography in Bhopal today?", session_id="test_s4")

    assert result["selected_sop"] is None
    # Must explicitly state that no SOP applies
    assert "no applicable" in result["response"].lower() or "no specific standard operating procedure" in result["response"].lower()


def test_graph_imd_severe_rain_overrides_activity(test_graph):
    # Severe rain depression (HAZ-001) trumps CYC-002
    gw = test_graph.weather_gateway
    gw.set_mock_location(Location(name="Bhopal", latitude=23.25, longitude=77.41))
    gw.set_mock_weather(WeatherState(
        temperature_2m=26.0,
        wind_speed_10m=25.0,
        wind_gusts_10m=48.0,
        precipitation=32.0,
        weather_code=65,
    ))

    result = test_graph.run("Can I cycle to work in Bhopal today?", session_id="test_s5")

    assert result["selected_sop"]["id"] == "HAZ-001"
    assert result["selected_sop"]["severity"] == "extreme"
    assert "HAZ-001" in result["response"]


def test_graph_session_memory_carry_forward(test_graph):
    gw = test_graph.weather_gateway
    gw.set_mock_location(Location(name="Bhopal", latitude=23.25, longitude=77.41))
    gw.set_mock_weather(WeatherState(
        temperature_2m=28.0,
        wind_speed_10m=41.0,
        wind_gusts_10m=44.0,
        precipitation=0.0,
    ))

    sess_id = "conversation_123"

    # Turn 1: User mentions Bhopal
    r1 = test_graph.run("Can I cycle in Bhopal today?", session_id=sess_id)
    assert r1["location"]["name"] == "Bhopal"

    # Turn 2: Follow-up question without naming Bhopal
    r2 = test_graph.run("What about running instead?", session_id=sess_id)
    # Location should be automatically carried from session memory
    assert r2["location_query"] == "Bhopal"
    assert r2["location"]["name"] == "Bhopal"
