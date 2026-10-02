import pytest
from app.policy.loader import load_policies
from app.policy.evaluator import PolicyEvaluator
from app.policy.models import EvaluationResult


@pytest.fixture
def registry():
    return load_policies("policies")


@pytest.fixture
def evaluator():
    return PolicyEvaluator()


def test_evaluate_bhopal_severe_rain_triggers_haz001(registry, evaluator):
    """
    Test the IMD heavy rain low-pressure system scenario in Bhopal:
    precipitation >= 30mm or precipitation >= 15mm with gusts >= 45 km/h.
    """
    haz_001 = registry.get("HAZ-001")
    assert haz_001 is not None

    bhopal_weather_context = {
        "activity": "cycling",
        "weather": {
            "precipitation": 34.5,
            "wind_gusts_10m": 52.0,
            "weather_code": 65,
        },
    }

    eval_result = evaluator.evaluate(haz_001, bhopal_weather_context)
    assert eval_result.result == EvaluationResult.TRUE
    assert eval_result.severity == "extreme"


def test_evaluate_cycling_wind_triggers_cyc001(registry, evaluator):
    """Wind speed >= 40 km/h triggers CYC-001 for cycling."""
    cyc_001 = registry.get("CYC-001")
    assert cyc_001 is not None

    windy_context = {
        "activity": "cycling",
        "weather": {
            "wind_speed_10m": 45.0,
            "wind_gusts_10m": 55.0,
        },
    }

    eval_result = evaluator.evaluate(cyc_001, windy_context)
    assert eval_result.result == EvaluationResult.TRUE


def test_evaluate_picnic_fuzzy_rec001_and_rec003(registry, evaluator):
    """
    Test picnic policies:
    - REC-001 triggers on damp ground/rain
    - REC-003 triggers on golden window
    """
    rec_001 = registry.get("REC-001")
    rec_003 = registry.get("REC-003")

    # Damp rainy day
    rainy_picnic = {
        "activity": "picnic",
        "weather": {
            "precipitation": 2.5,
            "precipitation_probability": 85,
        },
    }
    res_001 = evaluator.evaluate(rec_001, rainy_picnic)
    assert res_001.result == EvaluationResult.TRUE

    # Ideal sunny picnic day
    ideal_picnic = {
        "activity": "picnic",
        "weather": {
            "temperature_2m": 22.0,
            "precipitation": 0.0,
            "precipitation_probability": 5,
            "wind_speed_10m": 12.0,
        },
    }
    res_003 = evaluator.evaluate(rec_003, ideal_picnic)
    assert res_003.result == EvaluationResult.TRUE


def test_evaluate_all_candidate_policies(registry, evaluator):
    """Evaluating 25 policies returns results for all policies."""
    policies = registry.get_all()
    assert len(policies) == 25

    calm_context = {
        "activity": "cycling",
        "weather": {
            "temperature_2m": 20.0,
            "apparent_temperature": 20.0,
            "wind_speed_10m": 10.0,
            "wind_gusts_10m": 15.0,
            "precipitation": 0.0,
            "precipitation_probability": 0,
            "relative_humidity_2m": 50.0,
            "uv_index": 3.0,
            "visibility": 10000.0,
            "weather_code": 0,
        },
    }

    results = evaluator.evaluate_all(policies, calm_context)
    assert len(results) == 25

    # In calm pleasant weather, severe hazards must not trigger
    hazard_results = [r for r in results if r.policy_id.startswith("HAZ-")]
    for hr in hazard_results:
        assert hr.result == EvaluationResult.FALSE
