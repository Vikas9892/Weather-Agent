from __future__ import annotations

from typing import Any, Dict, List
from app.graph.state import SafetyState
from app.policy.evaluator import PolicyEvaluator
from app.policy.models import EvaluationResult, SOP
from app.policy.registry import PolicyRegistry
from app.policy.resolver import PolicyResolver


def retrieve_candidate_sops_node(
    state: SafetyState, registry: PolicyRegistry, evaluator: PolicyEvaluator
) -> Dict[str, Any]:
    """Retrieves relevant candidate SOPs filtered by activity and systemic hazard categories."""
    activity = state.get("activity", "general_outdoor")
    all_sops = registry.get_all()
    candidates = evaluator.select_candidates(all_sops, activity=activity)

    return {
        "candidate_sops": [p.model_dump() for p in candidates],
    }


def evaluate_sops_node(
    state: SafetyState, evaluator: PolicyEvaluator
) -> Dict[str, Any]:
    """Deterministically evaluates all candidate SOPs against the runtime weather context."""
    candidates_data = state.get("candidate_sops", [])
    candidates = [SOP.model_validate(c) for c in candidates_data]
    weather_ctx = state.get("weather", {})

    evaluated_list: List[Dict[str, Any]] = []
    matched_list: List[Dict[str, Any]] = []

    for c in candidates:
        evaluation = evaluator.evaluate(c, weather_ctx)
        evaluated_list.append(evaluation.model_dump())
        if evaluation.result == EvaluationResult.TRUE:
            matched_list.append(c.model_dump())

    return {
        "evaluated_sops": evaluated_list,
        "matched_sops": matched_list,
    }


def resolve_conflicts_node(
    state: SafetyState, resolver: PolicyResolver
) -> Dict[str, Any]:
    """Resolves precedence, overrides, and severity among matching SOPs."""
    matched_data = state.get("matched_sops", [])
    matched = [SOP.model_validate(m) for m in matched_data]

    resolution = resolver.resolve(matched)
    sel = resolution.selected_policy
    supp = resolution.supporting_policies

    return {
        "selected_sop": sel.model_dump() if sel else None,
        "supporting_sops": [s.model_dump() for s in supp],
        "policy_decision": {
            "decision": sel.decision_text if sel else None,
            "severity": sel.severity if sel else None,
            "rationale": sel.rationale_text if sel else None,
        } if sel else None,
        "resolution_reason": resolution.resolution_reason,
    }


def no_sop_fallback_node(state: SafetyState) -> Dict[str, Any]:
    """Generates an honest response when no safety SOP covers the query."""
    activity = state.get("activity", "this activity")
    loc_dict = state.get("location") or {}
    loc_name = loc_dict.get("name", "your area")
    weather = state.get("weather", {}).get("weather", {})
    temp = weather.get("temperature_2m", "")
    temp_str = f"({temp}°C) " if temp != "" else ""

    response_msg = (
        f"We evaluated live weather for {loc_name} {temp_str}and checked our policy registry, "
        f"but have no applicable Standard Operating Procedure (SOP) safety policy covering '{activity}'. "
        f"Our system strictly refrains from inventing safety advice. Please consult local authorities."
    )
    return {
        "selected_sop": None,
        "policy_decision": None,
        "response": response_msg,
        "safety_status": "APPROVED",
        "safety_reason": "No SOP matched; honest boundary response formulated.",
    }
