import pytest
from pathlib import Path
from backend.app.policy.loader import PolicyRegistry
from backend.app.policy.validator import validate_policy_set
from backend.app.policy.models import SOP, Condition, AllConditions, AnyConditions


def test_policies_load_and_validate():
    registry = PolicyRegistry()
    count = registry.load("policies")
    assert count == 25
    policies = registry.get_all()
    assert len(policies) == 25

    is_valid, errors = validate_policy_set(policies)
    assert is_valid
    assert len(errors) == 0


def test_policy_filtering():
    registry = PolicyRegistry()
    registry.load("policies")

    hazards = registry.filter_by_category("hazards")
    assert len(hazards) == 4

    cycling = registry.filter_by_category("cycling")
    assert len(cycling) == 4

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
