import pytest
from app.policy.loader import PolicyRegistry
from app.policy.validator import validate_policy_set
from app.policy.models import SOP, Condition, AllConditions, AnyConditions


def test_policies_load_and_validate():
    registry = PolicyRegistry()
    count = registry.load("policies")
    assert count >= 25
    policies = registry.get_all()
    assert len(policies) >= 25

    is_valid, errors = validate_policy_set(policies)
    assert is_valid
    assert len(errors) == 0


def test_policy_filtering():
    registry = PolicyRegistry()
    registry.load("policies")

    hazards = registry.filter_by_category("hazards")
    assert len(hazards) == 4

    cycling = registry.filter_by_category("cycling")
    assert len(cycling) >= 4

    exercise = registry.filter_by_category("exercise")
    assert len(exercise) == 4

    hiking = registry.filter_by_category("hiking")
    assert len(hiking) == 4

    recreation = registry.filter_by_category("recreation")
    assert len(recreation) == 3

    family = registry.filter_by_category("family")
    assert len(family) == 3

    travel = registry.filter_by_category("travel")
    assert len(travel) == 3


def test_imd_low_pressure_sop_present():
    registry = PolicyRegistry()
    registry.load("policies")
    sop = registry.get("HAZ-001")
    assert sop is not None
    assert sop.severity == "extreme"
    assert "CYC-002" in sop.overrides


def test_dynamic_sop_addition_without_code_changes(tmp_path):
    """
    Verifies that adding a new SOP YAML file requires ZERO Python code changes.
    The policy registry dynamically discovers, parses, validates, and activates it.
    """
    import yaml
    from pathlib import Path
    from app.policy.evaluator import PolicyEvaluator, EvaluationResult

    new_sop_path = Path("policies") / "cycling" / "CYC-006.yaml"
    sop_content = {
        "id": "CYC-006",
        "version": "1.0.0",
        "status": "active",
        "title": "Dense Coastal Salt Mist Corrosion & Traction Warning",
        "category": "cycling",
        "activities": ["cycling", "biking"],
        "severity": "moderate",
        "priority": 60,
        "conditions": {
            "all": [
                {"field": "weather.relative_humidity_2m", "operator": ">=", "value": 90.0},
                {"field": "weather.wind_speed_10m", "operator": ">=", "value": 25.0},
            ]
        },
        "evidence": ["weather.relative_humidity_2m", "weather.wind_speed_10m"],
        "decision": "Exercise caution. Damp maritime mist reduces brake pad friction.",
        "rationale": "High humidity above 90% combined with sustained wind creates salt-mist glazing on rims.",
        "tags": ["cycling", "mist", "traction"],
        "overrides": [],
        "source": "Coastal Commuter Safety Advisory",
        "effective_from": "2026-01-01",
    }

    try:
        with open(new_sop_path, "w", encoding="utf-8") as f:
            yaml.dump(sop_content, f)

        # Reload registry without modifying ANY Python control-flow code
        registry = PolicyRegistry()
        count = registry.load("policies")
        loaded_sop = registry.get("CYC-006")

        assert loaded_sop is not None
        assert loaded_sop.id == "CYC-006"
        assert loaded_sop.severity == "moderate"
        assert loaded_sop.priority == 60
        assert "cycling" in loaded_sop.activities

        # Verify condition evaluation works directly
        evaluator = PolicyEvaluator()
        result = evaluator.evaluate(
            loaded_sop,
            {"activity": "cycling", "weather": {"relative_humidity_2m": 92.0, "wind_speed_10m": 30.0}}
        )
        assert result.result == EvaluationResult.TRUE
        assert len(result.missing_evidence) == 0

    finally:
        if new_sop_path.exists():
            new_sop_path.unlink()

