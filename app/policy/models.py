from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvaluationResult(str, Enum):
    """Three-valued logic result for condition and policy evaluation."""
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


# Supported comparison operators (case-insensitive)
VALID_OPERATORS = {
    "==",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "in",
    "IN",
    "not_in",
    "NOT_IN",
    "contains",
    "CONTAINS",
}


class Condition(BaseModel):
    """Leaf condition testing a context field against a threshold."""
    field: str
    operator: str
    value: Any

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        if v not in VALID_OPERATORS and v.lower() not in {"in", "not_in", "contains"}:
            raise ValueError(f"Invalid operator '{v}'. Allowed: {sorted(list(VALID_OPERATORS))}")
        return v

    model_config = ConfigDict(extra="forbid")


class AllConditions(BaseModel):
    """Logical ALL (AND) container requiring all nested conditions to evaluate True."""
    all: List[ConditionNode]

    model_config = ConfigDict(extra="forbid")


class AnyConditions(BaseModel):
    """Logical ANY (OR) container requiring at least one nested condition to evaluate True."""
    any: List[ConditionNode]

    model_config = ConfigDict(extra="forbid")


class NotCondition(BaseModel):
    """Logical NOT container inverting the nested condition evaluation."""
    not_: ConditionNode = Field(alias="not")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


# ConditionNode composite type (ALL, ANY, NOT, leaf Condition)
ConditionNode = Union[AllConditions, AnyConditions, NotCondition, Condition]

AllConditions.model_rebuild()
AnyConditions.model_rebuild()
NotCondition.model_rebuild()


class EvidenceRequirement(BaseModel):
    """Explicit evidence requirements for policy execution."""
    required: List[str] = Field(default_factory=list)
    optional: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class SOP(BaseModel):
    """Standard Operating Procedure (SOP) safety policy definition."""
    id: str = Field(..., description="Unique alphanumeric identifier (e.g. CYC-001)")
    version: str = Field(default="1.0.0", description="Semantic version string")
    status: Literal["active", "draft", "deprecated"] = Field(
        default="active", description="Operational lifecycle status"
    )
    title: str = Field(..., description="Human-readable title of the rule")
    category: str = Field(
        ...,
        description="High-level category (cycling, exercise, hiking, recreation, family, travel, hazards)",
    )
    activities: List[str] = Field(
        default_factory=list,
        description="Specific outdoor activities covered by this policy",
    )
    severity: str = Field(
        ..., description="Risk severity tier (e.g. low, moderate, high, extreme, or CRITICAL)"
    )
    priority: int = Field(
        ...,
        description="Evaluation precedence (0-100, higher takes precedence)",
    )
    conditions: ConditionNode = Field(
        ..., description="Deterministic DSL condition tree"
    )
    evidence: Union[List[str], EvidenceRequirement, Dict[str, Any]] = Field(
        default_factory=list,
        description="Required weather metric fields (e.g. wind_speed_10m, precipitation)",
    )
    decision: Union[str, Dict[str, Any]] = Field(
        ..., description="The authoritative safety recommendation to issue"
    )
    rationale: Union[str, List[str]] = Field(
        ..., description="Underlying physical or meteorological safety reasoning"
    )
    tags: List[str] = Field(
        default_factory=list, description="Categorical or situational tags"
    )
    overrides: List[str] = Field(
        default_factory=list,
        description="List of policy IDs that this policy supersedes when triggered",
    )
    source: Union[str, Dict[str, Any]] = Field(
        default="project_defined", description="Standard authority / meteorological source (e.g. IMD, WHO, NWS)"
    )
    effective_from: str = Field(
        ..., description="Effective date or specification version reference"
    )

    model_config = ConfigDict(extra="ignore")

    @property
    def required_evidence(self) -> List[str]:
        """Extracts required evidence fields list regardless of representation."""
        if isinstance(self.evidence, list):
            return self.evidence
        if isinstance(self.evidence, EvidenceRequirement):
            return self.evidence.required
        if isinstance(self.evidence, dict):
            return self.evidence.get("required", [])
        return []

    @property
    def decision_text(self) -> str:
        """Normalized string representation of the decision."""
        if isinstance(self.decision, str):
            return self.decision
        if isinstance(self.decision, dict):
            return self.decision.get("action", str(self.decision))
        return str(self.decision)

    @property
    def rationale_text(self) -> str:
        """Normalized string representation of the rationale."""
        if isinstance(self.rationale, str):
            return self.rationale
        if isinstance(self.rationale, list):
            return "; ".join(self.rationale)
        return str(self.rationale)
