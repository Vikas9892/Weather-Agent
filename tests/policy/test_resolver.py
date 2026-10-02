import pytest
from app.policy.models import SOP, Condition, AllConditions
from app.policy.resolver import (
    PolicyResolver,
    calculate_condition_specificity,
    DecisionTrace,
)


def make_dummy_sop(id: str, severity: str, priority: int, overrides=None, specificity_count=1) -> SOP:
    conditions = (
        Condition(field="x", operator="==", value=1)
        if specificity_count == 1
        else AllConditions(
            all=[Condition(field=f"x_{i}", operator="==", value=i) for i in range(specificity_count)]
        )
    )
    return SOP(
        id=id,
        version="1.0.0",
        title=f"Test SOP {id}",
        category="testing",
        activities=["cycling"],
        severity=severity,
        priority=priority,
        conditions=conditions,
        decision=f"Action for {id}",
        rationale=f"Rationale for {id}",
        overrides=overrides or [],
        effective_from="2026-01-01",
    )


def test_conflict_resolution_overrides():
    resolver = PolicyResolver()
    # P1 overrides P2
    p1 = make_dummy_sop("HAZ-001", severity="extreme", priority=100, overrides=["CYC-002"])
    p2 = make_dummy_sop("CYC-002", severity="high", priority=70)

    result = resolver.resolve([p2, p1])
    assert result.selected_policy.id == "HAZ-001"
    assert ("CYC-002", "HAZ-001") in result.eliminated_by_override


def test_conflict_resolution_severity():
    resolver = PolicyResolver()
    # P1 extreme vs P2 moderate
    p1 = make_dummy_sop("P1", severity="extreme", priority=50)
    p2 = make_dummy_sop("P2", severity="moderate", priority=80)

    result = resolver.resolve([p2, p1])
    assert result.selected_policy.id == "P1"


def test_conflict_resolution_priority_when_severity_equal():
    resolver = PolicyResolver()
    p1 = make_dummy_sop("P1", severity="high", priority=75)
    p2 = make_dummy_sop("P2", severity="high", priority=85)

    result = resolver.resolve([p1, p2])
    assert result.selected_policy.id == "P2"


def test_conflict_resolution_specificity():
    resolver = PolicyResolver()
    # Same severity and priority, but P2 has 3 conditions vs P1 with 1 condition
    p1 = make_dummy_sop("P1", severity="high", priority=70, specificity_count=1)
    p2 = make_dummy_sop("P2", severity="high", priority=70, specificity_count=3)

    result = resolver.resolve([p1, p2])
    assert result.selected_policy.id == "P2"


def test_decision_trace_serialization():
    trace = DecisionTrace(
        query="Can I cycle in Bhopal?",
        intent={"activity": "cycling", "location": "Bhopal"},
        location={"city": "Bhopal", "latitude": 23.25, "longitude": 77.41},
        weather={"temperature_2m": 31.0, "precipitation": 25.0},
        candidate_policies=["CYC-001", "CYC-002", "HAZ-001"],
        matched_policies=["CYC-002", "HAZ-001"],
        selected_policy={"id": "HAZ-001", "severity": "extreme"},
        policy_decision={"action": "Cancel cycling"},
        safety_status="APPROVED",
        resolution_reason="HAZ-001 overrides CYC-002",
    )
    trace_dict = trace.model_dump()
    assert trace_dict["selected_policy"]["id"] == "HAZ-001"
    assert trace_dict["safety_status"] == "APPROVED"
