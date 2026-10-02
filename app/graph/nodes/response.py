from __future__ import annotations

from typing import Any, Dict
from app.graph.state import SafetyState
from app.llm.gateway import LLMGateway
from app.memory.session import SessionMemoryStore
from app.policy.models import SOP
from app.policy.resolver import DecisionTrace
from app.safety.validator import ResponseValidator
from app.weather.models import WeatherState


def generate_response_node(state: SafetyState, llm: LLMGateway) -> Dict[str, Any]:
    """Generates user-facing natural language response grounded in deterministic decisions."""
    # If response already set by an upstream branch (e.g. no_sop_fallback), skip regeneration
    if state.get("response"):
        return {"response": state["response"]}

    query = state.get("user_query", "")
    activity = state.get("activity", "outdoor activity")
    loc_dict = state.get("location") or {}
    loc_name = loc_dict.get("name", "your area")

    weather_raw = state.get("weather", {}).get("weather", {})
    selected_sop = state.get("selected_sop")
    safety_status = state.get("safety_status", "APPROVED")

    decision = None
    severity = None
    rationale = None
    if selected_sop:
        decision = selected_sop.get("decision")
        if isinstance(decision, dict):
            decision = decision.get("action", str(decision))
        severity = selected_sop.get("severity")
        rationale = selected_sop.get("rationale")
        if isinstance(rationale, list):
            rationale = "; ".join(rationale)

    resp_text = llm.generate_response(
        query=query,
        activity=activity,
        location_name=loc_name,
        weather_summary=weather_raw,
        selected_sop=selected_sop,
        safety_status=safety_status,
        decision=decision,
        severity=severity,
        rationale=rationale,
        supporting_sops=state.get("supporting_sops", []),
    )

    return {"response": resp_text}


def validate_response_node(state: SafetyState, validator: ResponseValidator) -> Dict[str, Any]:
    """Applies the 8 validation rules to ensure grounding and prevent hallucinations."""
    resp_text = state.get("response", "")
    sel_data = state.get("selected_sop")
    selected_sop = SOP.model_validate(sel_data) if sel_data else None

    weather_data = state.get("weather", {}).get("weather")
    weather = WeatherState.model_validate(weather_data) if weather_data else None

    loc_dict = state.get("location") or {}
    loc_name = loc_dict.get("name", "your area")
    activity = state.get("activity", "outdoor activity")

    val_result = validator.validate(
        response_text=resp_text,
        selected_sop=selected_sop,
        weather=weather,
        location_name=loc_name,
        activity=activity,
    )

    return {
        "response": val_result.final_response,
        "validation_result": val_result.model_dump(),
    }


def persist_session_node(state: SafetyState, memory: SessionMemoryStore) -> Dict[str, Any]:
    """Persists conversational state into session memory and compiles final DecisionTrace."""
    session_id = state.get("session_id", "default_session")
    query = state.get("user_query", "")
    resp = state.get("response", "")

    loc_dict = state.get("location") or {}
    loc_name = loc_dict.get("name")
    activity = state.get("activity")

    sel_data = state.get("selected_sop")
    sop_id = sel_data.get("id") if sel_data else None
    decision = state.get("policy_decision", {}).get("decision") if state.get("policy_decision") else None

    memory.update_session(
        session_id=session_id,
        user_query=query,
        response=resp,
        location=loc_name,
        activity=activity,
        sop_id=sop_id,
        decision=decision,
    )

    # Build machine-readable DecisionTrace
    trace = DecisionTrace(
        query=query,
        intent={
            "activity": activity,
            "location_query": state.get("location_query"),
            "requested_time": state.get("requested_time"),
        },
        location=loc_dict,
        weather=(state.get("weather") or {}).get("weather"),
        candidate_policies=[c.get("id") for c in state.get("candidate_sops", []) if c.get("id")],

        evaluations=state.get("evaluated_sops", []),
        matched_policies=[m.get("id") for m in state.get("matched_sops", []) if m.get("id")],
        selected_policy=sel_data,
        policy_decision=state.get("policy_decision"),
        safety_status=state.get("safety_status", "APPROVED"),
        resolution_reason=state.get("resolution_reason", ""),
        response_validation=state.get("validation_result"),
    )

    return {
        "decision_trace": trace.model_dump(),
    }
