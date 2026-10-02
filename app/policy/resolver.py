from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from app.policy.models import (
    SOP,
    AllConditions,
    AnyConditions,
    Condition,
    ConditionNode,
    NotCondition,
)

# Standardized severity tiers for deterministic comparison
SEVERITY_WEIGHTS: Dict[str, int] = {
    "emergency": 5,
    "critical": 5,
    "extreme": 5,
    "high": 4,
    "danger": 4,
    "warning": 3,
    "moderate": 3,
    "caution": 2,
    "low": 1,
    "advisory": 1,
    "info": 1,
}


def calculate_condition_specificity(node: ConditionNode) -> int:
    """
    Calculates the deterministic specificity of an SOP condition tree.
    Counts the total number of atomic leaf condition constraints evaluated.
    """
    if isinstance(node, Condition):
        return 1
    elif isinstance(node, AllConditions):
        return sum(calculate_condition_specificity(child) for child in node.all)
    elif isinstance(node, AnyConditions):
        return sum(calculate_condition_specificity(child) for child in node.any)
    elif isinstance(node, NotCondition):
        return 1 + calculate_condition_specificity(node.not_)
    return 1


class ResolutionResult(BaseModel):
    """The outcome of deterministic conflict resolution among matching SOPs."""
    selected_policy: Optional[SOP] = None
    supporting_policies: List[SOP] = Field(default_factory=list)
    eliminated_by_override: List[Tuple[str, str]] = Field(
        default_factory=list,
        description="Pairs of (eliminated_policy_id, overriding_policy_id)"
    )
    resolution_reason: str = ""


class PolicyResolver:
    """
    Deterministic conflict resolver for multi-matching SOP policies.
    
    Resolution order:
    1. Explicit override: If policy A explicitly lists policy B in overrides, B is eliminated.
    2. Severity: Higher risk tier trumps lower risk tier (e.g. Extreme > High > Moderate > Low).
    3. Priority: Deterministic integer priority (0-100, higher takes precedence).
    4. Specificity: More specific constraint trees trump generic rules.
    5. Stable tie-breaker: Lexicographical order by policy ID for strict determinism.
    """

    def resolve(self, matched_policies: List[SOP]) -> ResolutionResult:
        if not matched_policies:
            return ResolutionResult(
                selected_policy=None,
                supporting_policies=[],
                eliminated_by_override=[],
                resolution_reason="No policies matched runtime conditions."
            )

        if len(matched_policies) == 1:
            sole_policy = matched_policies[0]
            return ResolutionResult(
                selected_policy=sole_policy,
                supporting_policies=[],
                eliminated_by_override=[],
                resolution_reason=f"Sole matching policy: {sole_policy.id} ({sole_policy.title})."
            )

        # 1. Process explicit overrides
        overridden_ids: Set[str] = set()
        eliminated_pairs: List[Tuple[str, str]] = []

        for p in matched_policies:
            for target_id in p.overrides:
                overridden_ids.add(target_id)
                eliminated_pairs.append((target_id, p.id))

        active_candidates = [p for p in matched_policies if p.id not in overridden_ids]

        # Fallback if circular or mutual override eliminated all (safe guard)
        if not active_candidates:
            active_candidates = matched_policies

        # 2. Sort by: Severity (desc), Priority (desc), Specificity (desc), ID (asc)
        def sorting_key(p: SOP):
            sev_score = SEVERITY_WEIGHTS.get(p.severity.lower(), 1)
            priority_score = p.priority
            spec_score = calculate_condition_specificity(p.conditions)
            # In Python sorting, tuple compares element by element
            # We negate descending numeric keys so a standard sort can order them
            return (-sev_score, -priority_score, -spec_score, p.id)

        sorted_candidates = sorted(active_candidates, key=sorting_key)
        winner = sorted_candidates[0]
        supporting = [p for p in matched_policies if p.id != winner.id]

        reasons: List[str] = []
        if eliminated_pairs:
            override_texts = [f"{winner.id} overrides {t[0]}" for t in eliminated_pairs if t[1] == winner.id]
            if override_texts:
                reasons.append("; ".join(override_texts))

        reasons.append(
            f"Selected {winner.id} (Severity: {winner.severity.upper()}, Priority: {winner.priority}, Specificity: {calculate_condition_specificity(winner.conditions)})"
        )

        return ResolutionResult(
            selected_policy=winner,
            supporting_policies=supporting,
            eliminated_by_override=eliminated_pairs,
            resolution_reason=". ".join(reasons) + "."
        )


class DecisionTrace(BaseModel):
    """Machine-readable decision trace for full observability and explainability."""
    query: str
    intent: Dict[str, Any] = Field(default_factory=dict)
    location: Optional[Dict[str, Any]] = None
    weather: Optional[Dict[str, Any]] = None
    candidate_policies: List[str] = Field(default_factory=list)
    evaluations: List[Dict[str, Any]] = Field(default_factory=list)
    matched_policies: List[str] = Field(default_factory=list)
    selected_policy: Optional[Dict[str, Any]] = None
    policy_decision: Optional[Dict[str, Any]] = None
    safety_status: str = "APPROVED"
    resolution_reason: str = ""
    response_validation: Optional[Dict[str, Any]] = None
