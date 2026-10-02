from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.graph.state import SafetyState


class AssertionFailure(Exception):
    pass


def assert_selected_policy(state: SafetyState, expected_id: Optional[str]) -> None:
    sel = state.get("selected_sop")
    actual_id = sel.get("id") if sel else None
    if actual_id != expected_id:
        raise AssertionFailure(f"Expected selected SOP '{expected_id}', got '{actual_id}'. Response: {state.get('response')}")


def assert_severity(state: SafetyState, expected_severity: str) -> None:
    sel = state.get("selected_sop")
    actual_sev = sel.get("severity") if sel else state.get("policy_decision", {}).get("severity")
    if str(actual_sev).lower() != expected_severity.lower():
        raise AssertionFailure(f"Expected severity '{expected_severity}', got '{actual_sev}'")


def assert_safety_status(state: SafetyState, expected_status: str) -> None:
    actual = state.get("safety_status")
    if actual != expected_status:
        raise AssertionFailure(f"Expected safety status '{expected_status}', got '{actual}'")


def assert_response_contains(state: SafetyState, substring: str) -> None:
    resp = state.get("response", "")
    if substring.lower() not in resp.lower():
        raise AssertionFailure(f"Expected response to contain '{substring}', got: '{resp}'")


def assert_decision_trace_valid(state: SafetyState) -> None:
    trace = state.get("decision_trace")
    if not trace or not isinstance(trace, dict):
        raise AssertionFailure("Decision trace is missing or invalid.")
    for key in ["query", "intent", "safety_status", "candidate_policies"]:
        if key not in trace:
            raise AssertionFailure(f"Decision trace missing required key '{key}'")
