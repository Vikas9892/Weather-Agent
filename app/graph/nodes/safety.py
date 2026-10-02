from __future__ import annotations

from typing import Any, Dict
from app.graph.state import SafetyState
from app.policy.models import SOP
from app.safety.gate import SafetyGate
from app.weather.models import WeatherStatus


def safety_gate_node(state: SafetyState, gate: SafetyGate) -> Dict[str, Any]:
    """Applies deterministic safety gate checks before advice generation."""
    weather_status_str = state.get("weather_status", "valid")
    weather_status = WeatherStatus(weather_status_str) if weather_status_str in WeatherStatus._value2member_map_ else WeatherStatus.VALID

    matched_data = state.get("matched_sops", [])
    matched = [SOP.model_validate(m) for m in matched_data]

    sel_data = state.get("selected_sop")
    selected = SOP.model_validate(sel_data) if sel_data else None

    # Check if the selected policy itself lacks required evidence
    missing_evidence = []
    if selected:
        weather_ctx = state.get("weather", {})
        for req in selected.required_evidence:
            if req not in weather_ctx and (not isinstance(weather_ctx.get("weather"), dict) or req not in weather_ctx.get("weather", {})):
                missing_evidence.append(req)

    gate_result = gate.evaluate(
        weather_status=weather_status,
        matched_policies=matched,
        selected_policy=selected,
        missing_evidence=missing_evidence,
    )

    return {
        "safety_status": gate_result.status.value,
        "safety_reason": gate_result.reason,
    }

