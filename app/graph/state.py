from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class SafetyState(TypedDict, total=False):
    """
    Session-scoped state passed across LangGraph nodes.
    Maintains clean separation between weather facts, deterministic policy logic, and response.
    """
    # Session & raw input
    session_id: str
    user_query: str

    # Intent understanding
    activity: str
    location_query: Optional[str]
    requested_time: Optional[str]
    location: Optional[Dict[str, Any]]

    # Weather
    weather: Optional[Dict[str, Any]]
    weather_status: str
    weather_error: Optional[str]

    # Policies & evaluation
    candidate_sops: List[Dict[str, Any]]
    evaluated_sops: List[Dict[str, Any]]
    matched_sops: List[Dict[str, Any]]
    selected_sop: Optional[Dict[str, Any]]
    supporting_sops: List[Dict[str, Any]]
    policy_decision: Optional[Dict[str, Any]]
    resolution_reason: str

    # Safety gating & response
    safety_status: str
    safety_reason: str
    response: str
    validation_result: Optional[Dict[str, Any]]

    # Decision trace & terminal
    decision_trace: Optional[Dict[str, Any]]
    error: Optional[str]
