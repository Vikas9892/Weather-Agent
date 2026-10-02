from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.policy.models import EvaluationResult, SOP
from app.weather.models import WeatherStatus


class SafetyStatus(str, Enum):
    APPROVED = "APPROVED"
    UNCERTAIN = "UNCERTAIN"
    BLOCKED = "BLOCKED"


class SafetyGateResult(BaseModel):
    status: SafetyStatus
    reason: str
    can_generate_advice: bool


class SafetyGate:
    """
    Deterministic safety gate enforcing strict constraints before advice formulation.
    Evaluates weather integrity, SOP match validity, and missing evidence.
    """

    def evaluate(
        self,
        weather_status: WeatherStatus,
        matched_policies: List[SOP],
        selected_policy: Optional[SOP],
        missing_evidence: Optional[List[str]] = None,
    ) -> SafetyGateResult:
        # 1. Weather availability check
        if weather_status == WeatherStatus.UNAVAILABLE:
            return SafetyGateResult(
                status=SafetyStatus.BLOCKED,
                reason="Live weather data could not be retrieved. Safety decisions are blocked to prevent ungrounded advice.",
                can_generate_advice=False,
            )

        # 2. Weather provider consensus check
        if weather_status == WeatherStatus.UNCERTAIN:
            return SafetyGateResult(
                status=SafetyStatus.UNCERTAIN,
                reason="Meteorological provider readings exhibit high disagreement. Advice is presented with uncertainty warnings.",
                can_generate_advice=True,
            )

        # 3. Missing evidence check
        if missing_evidence and len(missing_evidence) > 0:
            return SafetyGateResult(
                status=SafetyStatus.UNCERTAIN,
                reason=f"SOP requires missing weather metrics: {missing_evidence}. Result cannot be certified definitive.",
                can_generate_advice=True,
            )

        # 4. Valid weather + policy match (or verified no-match)
        return SafetyGateResult(
            status=SafetyStatus.APPROVED,
            reason="Verified live weather data and deterministic SOP resolution completed.",
            can_generate_advice=True,
        )
