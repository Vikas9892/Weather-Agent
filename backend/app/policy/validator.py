from typing import Any, Dict, List, Set, Tuple

try:
    from .models import (
        SOP,
        AllConditions,
        AnyConditions,
        Condition,
        ConditionNode,
        NotCondition,
        VALID_OPERATORS,
    )
except ImportError:
    from app.policy.models import (
        SOP,
        AllConditions,
        AnyConditions,
        Condition,
        ConditionNode,
        NotCondition,
        VALID_OPERATORS,
    )


class PolicyValidationError(Exception):
    """Raised when policy validation fails."""
    pass


def validate_condition_operators(condition_node: ConditionNode, path: str = "conditions") -> List[str]:
    """Recursively checks condition tree for invalid operators."""
    errors: List[str] = []

    if isinstance(condition_node, Condition):
        if condition_node.operator not in VALID_OPERATORS:
            errors.append(
                f"{path}: Invalid operator '{condition_node.operator}'. Allowed: {VALID_OPERATORS}"
            )
    elif isinstance(condition_node, AllConditions):
        for idx, child in enumerate(condition_node.all):
            errors.extend(validate_condition_operators(child, f"{path}.all[{idx}]"))
    elif isinstance(condition_node, AnyConditions):
        for idx, child in enumerate(condition_node.any):
            errors.extend(validate_condition_operators(child, f"{path}.any[{idx}]"))
    elif isinstance(condition_node, NotCondition):
        errors.extend(validate_condition_operators(condition_node.not_, f"{path}.not"))
    elif isinstance(condition_node, dict):
        if "all" in condition_node:
            for idx, child in enumerate(condition_node["all"]):
                errors.extend(validate_condition_operators(child, f"{path}.all[{idx}]"))
        elif "any" in condition_node:
            for idx, child in enumerate(condition_node["any"]):
                errors.extend(validate_condition_operators(child, f"{path}.any[{idx}]"))
        elif "not" in condition_node:
            errors.extend(validate_condition_operators(condition_node["not"], f"{path}.not"))
        elif "operator" in condition_node:
            op = condition_node.get("operator")
            if op not in VALID_OPERATORS:
                errors.append(f"{path}: Invalid operator '{op}'. Allowed: {VALID_OPERATORS}")

    return errors


def validate_policy_set(policies: List[SOP]) -> Tuple[bool, List[str]]:
    """
    Validates a collection of SOP policies.
    Checks:
    1. No duplicate IDs.
    2. Valid operators in condition trees.
    3. No broken override references (every overridden ID must exist).
    """
    errors: List[str] = []
    seen_ids: Set[str] = set()
    policy_ids: Set[str] = {p.id for p in policies}

    for p in policies:
        # Check duplicate IDs
        if p.id in seen_ids:
            errors.append(f"Duplicate policy ID detected: '{p.id}'")
        seen_ids.add(p.id)

        # Check operators in condition tree
        op_errors = validate_condition_operators(p.conditions, path=f"{p.id}.conditions")
        errors.extend(op_errors)

        # Check override references
        for target_id in p.overrides:
            if target_id not in policy_ids:
                errors.append(
                    f"Policy '{p.id}' specifies override target '{target_id}', which does not exist in loaded policies."
                )

    is_valid = len(errors) == 0
    return is_valid, errors
