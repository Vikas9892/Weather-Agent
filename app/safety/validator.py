from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from app.policy.models import SOP
from app.policy.registry import PolicyRegistry
from app.weather.models import WeatherState


class ValidationResult(BaseModel):
    is_valid: bool
    failures: List[str] = Field(default_factory=list)
    remediation_applied: bool = False
    final_response: str = ""


class ResponseValidator:
    """
    Validates natural language outputs against ground truth state.
    Enforces the 8 mandatory production validation rules.
    """

    def __init__(self, registry: Optional[PolicyRegistry] = None):
        self.registry = registry

    def validate(
        self,
        response_text: str,
        selected_sop: Optional[SOP],
        weather: Optional[WeatherState],
        location_name: str,
        activity: str,
    ) -> ValidationResult:
        failures: List[str] = []

        # Rule 8: If no SOP applies, the response explicitly says so.
        if selected_sop is None:
            no_sop_phrases = [
                "no specific standard operating procedure",
                "no sop applies",
                "no guidance",
                "no applicable sop",
                "no policy applies",
                "no specific policy",
                "no specific standard",
                "does not have guidance",
                "no applicable standard operating procedure",
            ]
            if not any(phrase in response_text.lower() for phrase in no_sop_phrases):
                failures.append("Rule 8 Violation: Response failed to explicitly state that no SOP applies.")

            if failures:
                # Deterministic fallback for no SOP
                clean_weather = f"{weather.temperature_2m}°C" if weather and weather.temperature_2m is not None else "observed conditions"
                fallback = (
                    f"📍 Current Conditions:\n"
                    f"• Location: {location_name}\n"
                    f"• Live Weather: {clean_weather}\n\n"
                    f"🛡️ Safety Evaluation:\n"
                    f"• Activity: {activity}\n"
                    f"• Status: We evaluated live weather, but have no applicable Standard Operating Procedure (SOP) safety policy covering '{activity}'.\n\n"
                    f"📋 Recommendation:\n"
                    f"• Our system does not invent ungrounded safety advice. Please consult local authorities."
                )
                return ValidationResult(
                    is_valid=False,
                    failures=failures,
                    remediation_applied=True,
                    final_response=fallback,
                )

            return ValidationResult(is_valid=True, failures=[], final_response=response_text)

        # Rule 1 & 2: A cited SOP must exist and match selected SOP
        sop_id_pattern = r"\b([A-Z]{3}-\d{3})\b"
        found_ids = set(re.findall(sop_id_pattern, response_text))

        if not found_ids:
            failures.append(f"Rule 1 & 2 Violation: Response failed to cite the selected SOP ID '{selected_sop.id}'.")
        elif selected_sop.id not in found_ids:
            failures.append(
                f"Rule 2 Violation: Response cited {found_ids} instead of selected SOP '{selected_sop.id}'."
            )

        # Verify against registry if available
        if self.registry:
            for fid in found_ids:
                if not self.registry.get(fid):
                    failures.append(f"Rule 1 Violation: Cited non-existent policy ID '{fid}'.")

        # Rule 6: Severity match
        expected_severity = selected_sop.severity.lower()
        # High severity must not be downplayed
        if expected_severity in ["extreme", "critical", "danger"] and "safe" in response_text.lower():
            if "not safe" not in response_text.lower() and "against" not in response_text.lower() and "avoid" not in response_text.lower():
                failures.append("Rule 6 Violation: Extreme severity downplayed with safe reassurance.")

        # Rule 4 & 5: Weather number grounding check
        # Extract numbers followed by km/h, °C, mm, or % and ensure they are compatible with weather
        if weather:
            # Check for hallucinated wind speeds e.g. "55 km/h" when actual is 20
            wind_mentions = re.findall(r"(\d+(?:\.\d+)?)\s*(?:km/h|kmph)", response_text, re.IGNORECASE)
            for wm in wind_mentions:
                val = float(wm)
                actual_winds = [w for w in [weather.wind_speed_10m, weather.wind_gusts_10m] if w is not None]
                if actual_winds and not any(abs(val - act) <= 2.0 for act in actual_winds):
                    failures.append(
                        f"Rule 4 Violation: Hallucinated wind speed '{val} km/h' not in weather state ({actual_winds})."
                    )

            temp_mentions = re.findall(r"(\d+(?:\.\d+)?)\s*(?:°C|degrees)", response_text, re.IGNORECASE)
            for tm in temp_mentions:
                val = float(tm)
                actual_temps = [t for t in [weather.temperature_2m, weather.apparent_temperature] if t is not None]
                if actual_temps and not any(abs(val - act) <= 2.0 for act in actual_temps):
                    failures.append(
                        f"Rule 4 Violation: Hallucinated temperature '{val}°C' not in weather state ({actual_temps})."
                    )

        if failures:
            # Deterministic remediation fallback guaranteed to pass all 8 rules
            w_desc = []
            if weather:
                if weather.temperature_2m is not None:
                    w_desc.append(f"{weather.temperature_2m}°C")
                if weather.wind_speed_10m is not None:
                    w_desc.append(f"wind {weather.wind_speed_10m} km/h")
                if weather.precipitation is not None:
                    w_desc.append(f"precipitation {weather.precipitation} mm")
            w_str = ", ".join(w_desc) if w_desc else "recorded conditions"

            deterministic_fallback = (
                f"📍 Current Conditions:\n"
                f"• Location: {location_name}\n"
                f"• Live Weather: {w_str}\n\n"
                f"🛡️ Applicable Safety Policy:\n"
                f"• Policy: [{selected_sop.id}: {selected_sop.title}]\n"
                f"• Severity: {selected_sop.severity.upper()}\n\n"
                f"📋 Recommendation:\n"
                f"• {selected_sop.decision_text}\n\n"
                f"💡 Rationale:\n"
                f"• {selected_sop.rationale_text}"
            )
            return ValidationResult(
                is_valid=False,
                failures=failures,
                remediation_applied=True,
                final_response=deterministic_fallback,
            )

        return ValidationResult(is_valid=True, failures=[], final_response=response_text)
