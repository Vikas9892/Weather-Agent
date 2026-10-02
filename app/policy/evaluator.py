from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

from app.policy.models import (
    SOP,
    AllConditions,
    AnyConditions,
    Condition,
    ConditionNode,
    EvaluationResult,
    NotCondition,
)


def extract_field_value(field_path: str, context: Dict[str, Any]) -> Tuple[Any, bool]:
    """
    Extracts a value from the evaluation context using dot-notation or fallback lookup.
    
    Examples:
    - field_path='weather.wind_speed', context={'weather': {'wind_speed': 42}} -> (42, True)
    - field_path='wind_speed_10m', context={'weather': {'wind_speed_10m': 42}} -> (42, True)
    - field_path='weather.temperature_2m', context={'temperature_2m': 30} -> (30, True)
    """
    if not context or not isinstance(context, dict):
        return None, False

    # 1. Direct key match (e.g. context['activity'] or context['weather.wind_speed'])
    if field_path in context and context[field_path] is not None:
        return context[field_path], True

    # 2. Nested dot-path traversal (e.g. context['weather']['wind_speed'])
    parts = field_path.split(".")
    curr: Any = context
    found = True
    for part in parts:
        if isinstance(curr, dict) and part in curr:
            curr = curr[part]
        else:
            found = False
            break

    if found and curr is not None:
        return curr, True

    # 3. Flexible fallback: if prefixed with 'weather.', check context['weather'] or flat context
    if field_path.startswith("weather."):
        stripped = field_path[len("weather.") :]
        # Check flat context
        if stripped in context and context[stripped] is not None:
            return context[stripped], True
        # Check nested weather if context has weather dict
        weather_dict = context.get("weather")
        if isinstance(weather_dict, dict) and stripped in weather_dict and weather_dict[stripped] is not None:
            return weather_dict[stripped], True

    # 4. Flexible fallback: if non-prefixed, check inside context['weather']
    weather_dict = context.get("weather")
    if isinstance(weather_dict, dict) and field_path in weather_dict and weather_dict[field_path] is not None:
        return weather_dict[field_path], True

    return None, False


def evaluate_leaf_condition(condition: Condition, context: Dict[str, Any]) -> Tuple[EvaluationResult, str]:
    """
    Evaluates a single leaf Condition against context.
    Returns (EvaluationResult, reason_str).
    """
    actual_value, exists = extract_field_value(condition.field, context)

    # Missing evidence check
    if not exists or actual_value is None:
        return (
            EvaluationResult.UNKNOWN,
            f"Field '{condition.field}' is missing or null in context",
        )

    op = condition.operator.strip().lower()
    target_value = condition.value

    try:
        if op == "==":
            if isinstance(actual_value, str) and isinstance(target_value, str):
                matched = actual_value.strip().lower() == target_value.strip().lower()
            else:
                matched = actual_value == target_value
            res = EvaluationResult.TRUE if matched else EvaluationResult.FALSE
            return res, f"{condition.field} ({actual_value}) == {target_value} -> {res.value}"

        elif op == "!=":
            if isinstance(actual_value, str) and isinstance(target_value, str):
                matched = actual_value.strip().lower() != target_value.strip().lower()
            else:
                matched = actual_value != target_value
            res = EvaluationResult.TRUE if matched else EvaluationResult.FALSE
            return res, f"{condition.field} ({actual_value}) != {target_value} -> {res.value}"

        elif op in (">", "gt"):
            matched = float(actual_value) > float(target_value)
            res = EvaluationResult.TRUE if matched else EvaluationResult.FALSE
            return res, f"{condition.field} ({actual_value}) > {target_value} -> {res.value}"

        elif op in (">=", "gte", "ge"):
            matched = float(actual_value) >= float(target_value)
            res = EvaluationResult.TRUE if matched else EvaluationResult.FALSE
            return res, f"{condition.field} ({actual_value}) >= {target_value} -> {res.value}"

        elif op in ("<", "lt"):
            matched = float(actual_value) < float(target_value)
            res = EvaluationResult.TRUE if matched else EvaluationResult.FALSE
            return res, f"{condition.field} ({actual_value}) < {target_value} -> {res.value}"

        elif op in ("<=", "lte", "le"):
            matched = float(actual_value) <= float(target_value)
            res = EvaluationResult.TRUE if matched else EvaluationResult.FALSE
            return res, f"{condition.field} ({actual_value}) <= {target_value} -> {res.value}"

        elif op == "in":
            # target_value must be an iterable/collection
            if isinstance(target_value, (list, tuple, set)):
                if isinstance(actual_value, str):
                    target_set = {str(x).lower() for x in target_value}
                    matched = actual_value.strip().lower() in target_set
                else:
                    matched = actual_value in target_value
            elif isinstance(target_value, str) and isinstance(actual_value, str):
                matched = actual_value.strip().lower() in target_value.strip().lower()
            else:
                matched = False
            res = EvaluationResult.TRUE if matched else EvaluationResult.FALSE
            return res, f"{condition.field} ({actual_value}) in {target_value} -> {res.value}"

        elif op == "not_in":
            if isinstance(target_value, (list, tuple, set)):
                if isinstance(actual_value, str):
                    target_set = {str(x).lower() for x in target_value}
                    matched = actual_value.strip().lower() not in target_set
                else:
                    matched = actual_value not in target_value
            else:
                matched = True
            res = EvaluationResult.TRUE if matched else EvaluationResult.FALSE
            return res, f"{condition.field} ({actual_value}) not_in {target_value} -> {res.value}"

        elif op == "contains":
            if isinstance(actual_value, (list, tuple, set)):
                matched = target_value in actual_value
            elif isinstance(actual_value, str) and isinstance(target_value, str):
                matched = target_value.strip().lower() in actual_value.strip().lower()
            else:
                matched = False
            res = EvaluationResult.TRUE if matched else EvaluationResult.FALSE
            return res, f"{condition.field} ({actual_value}) contains {target_value} -> {res.value}"

        else:
            return EvaluationResult.UNKNOWN, f"Unsupported operator '{condition.operator}'"

    except (ValueError, TypeError) as e:
        return EvaluationResult.UNKNOWN, f"Type mismatch comparing {actual_value} with {target_value}: {e}"


def evaluate_condition_node(
    node: ConditionNode, context: Dict[str, Any]
) -> Tuple[EvaluationResult, List[str]]:
    """
    Recursively evaluates a condition node using Kleene three-valued logic (TRUE, FALSE, UNKNOWN).
    Returns (EvaluationResult, list of trace explanation strings).
    """
    traces: List[str] = []

    if isinstance(node, Condition):
        res, trace = evaluate_leaf_condition(node, context)
        traces.append(trace)
        return res, traces

    if isinstance(node, AllConditions):
        has_unknown = False
        for child in node.all:
            child_res, child_traces = evaluate_condition_node(child, context)
            traces.extend(child_traces)
            if child_res == EvaluationResult.FALSE:
                return EvaluationResult.FALSE, traces
            elif child_res == EvaluationResult.UNKNOWN:
                has_unknown = True

        if has_unknown:
            return EvaluationResult.UNKNOWN, traces
        return EvaluationResult.TRUE, traces

    if isinstance(node, AnyConditions):
        has_unknown = False
        all_false = True
        for child in node.any:
            child_res, child_traces = evaluate_condition_node(child, context)
            traces.extend(child_traces)
            if child_res == EvaluationResult.TRUE:
                return EvaluationResult.TRUE, traces
            elif child_res == EvaluationResult.UNKNOWN:
                has_unknown = True
                all_false = False
            elif child_res == EvaluationResult.FALSE:
                pass

        if has_unknown:
            return EvaluationResult.UNKNOWN, traces
        if all_false:
            return EvaluationResult.FALSE, traces
        return EvaluationResult.FALSE, traces

    if isinstance(node, NotCondition):
        child_res, child_traces = evaluate_condition_node(node.not_, context)
        traces.extend(child_traces)
        if child_res == EvaluationResult.TRUE:
            return EvaluationResult.FALSE, traces
        elif child_res == EvaluationResult.FALSE:
            return EvaluationResult.TRUE, traces
        else:
            return EvaluationResult.UNKNOWN, traces

    return EvaluationResult.UNKNOWN, [f"Unrecognized condition node type: {type(node)}"]


class PolicyEvaluation(BaseModel):
    """Evaluation result for an individual policy against weather and activity context."""
    policy_id: str
    result: EvaluationResult
    severity: str
    priority: int
    matched_conditions: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    explanation: str = ""


class PolicyEvaluator:
    """Deterministic policy engine evaluating SOP conditions against runtime context."""

    def evaluate(self, policy: SOP, context: Dict[str, Any]) -> PolicyEvaluation:
        """
        Evaluates a single SOP against the provided context.
        First validates required evidence; if evidence is missing, returns UNKNOWN.
        Then evaluates the condition tree deterministically.
        """
        # 1. Evidence validation: verify all required evidence fields exist
        missing_evidence: List[str] = []
        for req_field in policy.required_evidence:
            _, exists = extract_field_value(req_field, context)
            if not exists:
                missing_evidence.append(req_field)

        if missing_evidence:
            return PolicyEvaluation(
                policy_id=policy.id,
                result=EvaluationResult.UNKNOWN,
                severity=policy.severity,
                priority=policy.priority,
                missing_evidence=missing_evidence,
                explanation=f"Required evidence missing: {missing_evidence}",
            )

        # 2. Evaluate condition tree
        res, traces = evaluate_condition_node(policy.conditions, context)

        return PolicyEvaluation(
            policy_id=policy.id,
            result=res,
            severity=policy.severity,
            priority=policy.priority,
            matched_conditions=traces,
            missing_evidence=[],
            explanation=f"Policy evaluated to {res.value}. Traces: {'; '.join(traces)}",
        )

    def select_candidates(
        self,
        policies: List[SOP],
        activity: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[SOP]:
        """
        Pre-filters candidate SOPs before deterministic evaluation based on activity,
        category, and tags. Hazard policies ('hazards' category or 'all' activity) are
        always retained as candidate safeguards.
        """
        if not activity and not category and not tags:
            return policies

        candidates: List[SOP] = []
        act_lower = activity.lower().strip() if activity else None
        cat_lower = category.lower().strip() if category else None
        tags_set = {t.lower().strip() for t in tags} if tags else set()

        for p in policies:
            # 1. Systemic hazards always qualify as candidate safeguards
            if p.category.lower() == "hazards" or any(a.lower() == "all" for a in p.activities):
                candidates.append(p)
                continue

            # 2. Activity match
            if act_lower and any(act_lower == a.lower() for a in p.activities):
                candidates.append(p)
                continue

            # 3. Category match
            if cat_lower and p.category.lower() == cat_lower:
                candidates.append(p)
                continue

            # 4. Tag overlap
            if tags_set and any(t.lower() in tags_set for t in p.tags):
                candidates.append(p)
                continue

        # Preserve deterministic order by ID
        return sorted(list({p.id: p for p in candidates}.values()), key=lambda x: x.id)

    def evaluate_all(
        self, policies: List[SOP], context: Dict[str, Any]
    ) -> List[PolicyEvaluation]:
        """Evaluates a collection of candidate policies."""
        return [self.evaluate(p, context) for p in policies]

