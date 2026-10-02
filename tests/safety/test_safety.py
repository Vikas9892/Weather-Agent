import pytest
from app.policy.models import SOP, Condition
from app.policy.registry import PolicyRegistry
from app.safety.gate import SafetyGate, SafetyStatus
from app.safety.validator import ResponseValidator
from app.weather.models import WeatherState, WeatherStatus


@pytest.fixture
def sample_sop():
    return SOP(
        id="CYC-001",
        version="1.0.0",
        title="Cycling Wind Risk",
        category="cycling",
        activities=["cycling"],
        severity="high",
        priority=75,
        conditions=Condition(field="wind_speed", operator=">=", value=40.0),
        evidence=["wind_speed"],
        decision="Avoid cycling",
        rationale="Strong winds destabilize bikes",
        effective_from="2026-01-01",
    )


def test_safety_gate_status_approved(sample_sop):
    gate = SafetyGate()
    result = gate.evaluate(
        weather_status=WeatherStatus.VALID,
        matched_policies=[sample_sop],
        selected_policy=sample_sop,
        missing_evidence=[],
    )
    assert result.status == SafetyStatus.APPROVED
    assert result.can_generate_advice is True


def test_safety_gate_status_blocked_on_weather_failure(sample_sop):
    gate = SafetyGate()
    result = gate.evaluate(
        weather_status=WeatherStatus.UNAVAILABLE,
        matched_policies=[],
        selected_policy=None,
    )
    assert result.status == SafetyStatus.BLOCKED
    assert result.can_generate_advice is False


def test_safety_gate_status_uncertain_on_missing_evidence(sample_sop):
    gate = SafetyGate()
    result = gate.evaluate(
        weather_status=WeatherStatus.VALID,
        matched_policies=[sample_sop],
        selected_policy=sample_sop,
        missing_evidence=["wind_gust"],
    )
    assert result.status == SafetyStatus.UNCERTAIN


def test_response_validator_valid_citation(sample_sop):
    validator = ResponseValidator()
    weather = WeatherState(temperature_2m=25.0, wind_speed_10m=42.0)
    good_text = "In Bhopal, wind speed is 42 km/h. Under safety policy CYC-001, we advise avoiding cycling."

    res = validator.validate(
        response_text=good_text,
        selected_sop=sample_sop,
        weather=weather,
        location_name="Bhopal",
        activity="cycling",
    )
    assert res.is_valid is True
    assert len(res.failures) == 0


def test_response_validator_detects_hallucinated_weather_numbers(sample_sop):
    validator = ResponseValidator()
    weather = WeatherState(temperature_2m=25.0, wind_speed_10m=20.0)
    # Claims 65 km/h when actual is 20 km/h
    hallucinated_text = "In Bhopal, wind speed is 65 km/h. Under safety policy CYC-001, avoid cycling."

    res = validator.validate(
        response_text=hallucinated_text,
        selected_sop=sample_sop,
        weather=weather,
        location_name="Bhopal",
        activity="cycling",
    )
    assert res.is_valid is False
    assert any("Hallucinated wind speed" in f for f in res.failures)
    assert res.remediation_applied is True
    # The remediated response must be clean and grounded
    assert "CYC-001" in res.final_response


def test_response_validator_no_sop_requires_explicit_statement():
    validator = ResponseValidator()
    weather = WeatherState(temperature_2m=22.0)
    # Casual response without explicitly stating that no SOP applies
    bad_text = "It looks pretty pleasant outside, go ahead and have fun!"

    res = validator.validate(
        response_text=bad_text,
        selected_sop=None,
        weather=weather,
        location_name="Bhopal",
        activity="bird_watching",
    )
    assert res.is_valid is False
    assert any("no SOP applies" in f for f in res.failures)
    assert "no applicable Standard Operating Procedure" in res.final_response
