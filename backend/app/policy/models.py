from __future__ import annotations

from typing import Any, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

# Valid operators for conditions
Operator = Literal[
    ">",
    ">=",
    "<",
    "<=",
    "==",
    "!=",
    "in",
    "not_in",
    "contains",
]

VALID_OPERATORS = {">", ">=", "<", "<=", "==", "!=", "in", "not_in", "contains"}


class Condition(BaseModel):
    """Leaf condition testing a weather fact field against a threshold."""
    field: str
    operator: Operator
    value: Any

    model_config = ConfigDict(extra="forbid")


class AllConditions(BaseModel):
    """Logical AND container requiring all nested conditions to evaluate True."""
    all: List[ConditionNode]

    model_config = ConfigDict(extra="forbid")


class AnyConditions(BaseModel):
    """Logical OR container requiring at least one nested condition to evaluate True."""
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
    severity: Literal["low", "moderate", "high", "extreme"] = Field(
        ..., description="Risk severity tier"
    )
    priority: int = Field(
        ...,
        description="Evaluation precedence (higher integer takes precedence in resolution)",
    )
    conditions: ConditionNode = Field(
        ..., description="Deterministic DSL condition tree"
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Required weather metric fields (e.g. wind_speed_10m, precipitation)",
    )
    decision: str = Field(
        ..., description="The authoritative safety recommendation to issue"
    )
    rationale: str = Field(
        ..., description="Underlying physical or meteorological safety reasoning"
    )
    tags: List[str] = Field(
        default_factory=list, description="Categorical or situational tags"
    )
    overrides: List[str] = Field(
        default_factory=list,
        description="List of policy IDs that this policy supersedes when triggered",
    )
    source: str = Field(
        ..., description="Standard authority / meteorological source (e.g. IMD, WHO, NWS)"
    )
    effective_from: str = Field(
        ..., description="Effective date or specification version reference"
    )

    model_config = ConfigDict(extra="forbid")
