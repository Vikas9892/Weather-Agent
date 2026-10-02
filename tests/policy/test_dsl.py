import pytest
from app.policy.models import (
    Condition,
    AllConditions,
    AnyConditions,
    NotCondition,
    EvaluationResult,
    SOP,
)
from app.policy.evaluator import (
    PolicyEvaluator,
    evaluate_leaf_condition,
    evaluate_condition_node,
    extract_field_value,
)


def test_extract_field_value():
    context = {
        "activity": "cycling",
        "weather": {
            "wind_speed": 42.5,
            "temperature_2m": 31.0,
        },
        "flat_val": 100,
    }

    # Direct flat
    val, exists = extract_field_value("flat_val", context)
    assert exists and val == 100

    # Dot notation
    val, exists = extract_field_value("weather.wind_speed", context)
    assert exists and val == 42.5

    # Fallback to nested
    val, exists = extract_field_value("wind_speed", context)
    assert exists and val == 42.5

    # Missing
    val, exists = extract_field_value("weather.snow_depth", context)
    assert not exists and val is None


def test_comparison_operators():
    context = {
        "wind_speed": 40.0,
        "temperature": 25.0,
        "activity": "hiking",
        "tags": ["outdoor", "summer"],
    }

    # Greater than
    cond_gt = Condition(field="wind_speed", operator=">", value=35.0)
    res, _ = evaluate_leaf_condition(cond_gt, context)
    assert res == EvaluationResult.TRUE

    cond_gt_fail = Condition(field="wind_speed", operator=">", value=45.0)
    res, _ = evaluate_leaf_condition(cond_gt_fail, context)
    assert res == EvaluationResult.FALSE

    # Greater than or equal
    cond_gte = Condition(field="wind_speed", operator=">=", value=40.0)
    res, _ = evaluate_leaf_condition(cond_gte, context)
    assert res == EvaluationResult.TRUE

    # Less than
    cond_lt = Condition(field="temperature", operator="<", value=30.0)
    res, _ = evaluate_leaf_condition(cond_lt, context)
    assert res == EvaluationResult.TRUE

    # Less than or equal
    cond_lte = Condition(field="temperature", operator="<=", value=25.0)
    res, _ = evaluate_leaf_condition(cond_lte, context)
    assert res == EvaluationResult.TRUE

    # Equal
    cond_eq = Condition(field="activity", operator="==", value="HIKING")
    res, _ = evaluate_leaf_condition(cond_eq, context)
    assert res == EvaluationResult.TRUE

    # Not equal
    cond_neq = Condition(field="activity", operator="!=", value="cycling")
    res, _ = evaluate_leaf_condition(cond_neq, context)
    assert res == EvaluationResult.TRUE

    # IN operator
    cond_in = Condition(field="activity", operator="IN", value=["running", "hiking", "cycling"])
    res, _ = evaluate_leaf_condition(cond_in, context)
    assert res == EvaluationResult.TRUE

    # NOT_IN operator
    cond_notin = Condition(field="activity", operator="NOT_IN", value=["swimming", "skiing"])
    res, _ = evaluate_leaf_condition(cond_notin, context)
    assert res == EvaluationResult.TRUE

    # CONTAINS operator
    cond_contains = Condition(field="tags", operator="contains", value="summer")
    res, _ = evaluate_leaf_condition(cond_contains, context)
    assert res == EvaluationResult.TRUE


def test_logical_operators_all_any_not():
    context = {
        "activity": "cycling",
        "wind_speed": 42.0,
        "temperature": 15.0,
    }

    # ALL matches
    all_cond = AllConditions(
        all=[
            Condition(field="activity", operator="==", value="cycling"),
            Condition(field="wind_speed", operator=">=", value=35.0),
        ]
    )
    res, _ = evaluate_condition_node(all_cond, context)
    assert res == EvaluationResult.TRUE

    # ANY matches one
    any_cond = AnyConditions(
        any=[
            Condition(field="temperature", operator=">=", value=40.0),
            Condition(field="wind_speed", operator=">=", value=40.0),
        ]
    )
    res, _ = evaluate_condition_node(any_cond, context)
    assert res == EvaluationResult.TRUE

    # NOT inverts
    not_cond = NotCondition(
        not_=Condition(field="temperature", operator="<", value=10.0)
    )
    res, _ = evaluate_condition_node(not_cond, context)
    assert res == EvaluationResult.TRUE


def test_nested_dsl_conditions():
    # ALL with nested ANY
    nested = AllConditions(
        all=[
            Condition(field="activity", operator="==", value="cycling"),
            AnyConditions(
                any=[
                    Condition(field="wind_speed", operator=">=", value=35.0),
                    Condition(field="temperature", operator=">=", value=40.0),
                ]
            ),
        ]
    )

    context_match = {"activity": "cycling", "wind_speed": 38.0, "temperature": 22.0}
    res, _ = evaluate_condition_node(nested, context_match)
    assert res == EvaluationResult.TRUE

    context_no_match = {"activity": "running", "wind_speed": 38.0, "temperature": 22.0}
    res, _ = evaluate_condition_node(nested, context_no_match)
    assert res == EvaluationResult.FALSE


def test_three_valued_unknown_logic():
    # Missing evidence yields UNKNOWN
    context_missing = {"activity": "cycling"}  # wind_speed missing

    cond = Condition(field="wind_speed", operator=">=", value=35.0)
    res, _ = evaluate_leaf_condition(cond, context_missing)
    assert res == EvaluationResult.UNKNOWN

    # In ALL: False and Unknown is False
    all_with_false = AllConditions(
        all=[
            Condition(field="activity", operator="==", value="swimming"),  # False
            Condition(field="wind_speed", operator=">=", value=35.0),       # Unknown
        ]
    )
    res, _ = evaluate_condition_node(all_with_false, context_missing)
    assert res == EvaluationResult.FALSE

    # In ALL: True and Unknown is Unknown
    all_with_true = AllConditions(
        all=[
            Condition(field="activity", operator="==", value="cycling"),   # True
            Condition(field="wind_speed", operator=">=", value=35.0),       # Unknown
        ]
    )
    res, _ = evaluate_condition_node(all_with_true, context_missing)
    assert res == EvaluationResult.UNKNOWN

    # In ANY: True or Unknown is True
    any_with_true = AnyConditions(
        any=[
            Condition(field="activity", operator="==", value="cycling"),   # True
            Condition(field="wind_speed", operator=">=", value=35.0),       # Unknown
        ]
    )
    res, _ = evaluate_condition_node(any_with_true, context_missing)
    assert res == EvaluationResult.TRUE

    # In ANY: False or Unknown is Unknown
    any_with_false = AnyConditions(
        any=[
            Condition(field="activity", operator="==", value="swimming"),  # False
            Condition(field="wind_speed", operator=">=", value=35.0),       # Unknown
        ]
    )
    res, _ = evaluate_condition_node(any_with_false, context_missing)
    assert res == EvaluationResult.UNKNOWN


def test_evidence_validation_in_policy():
    evaluator = PolicyEvaluator()
    policy = SOP(
        id="TEST-001",
        version="1.0.0",
        title="Test Wind Hazard",
        category="cycling",
        activities=["cycling"],
        severity="high",
        priority=80,
        conditions=Condition(field="wind_speed", operator=">=", value=35.0),
        evidence=["wind_speed", "wind_gust"],
        decision="Avoid cycling",
        rationale="High wind instability",
        effective_from="2026-01-01",
    )

    # Missing one required field ("wind_gust")
    context = {"activity": "cycling", "wind_speed": 40.0}
    evaluation = evaluator.evaluate(policy, context)
    assert evaluation.result == EvaluationResult.UNKNOWN
    assert "wind_gust" in evaluation.missing_evidence

    # All required evidence present
    context_complete = {"activity": "cycling", "wind_speed": 40.0, "wind_gust": 55.0}
    evaluation_complete = evaluator.evaluate(policy, context_complete)
    assert evaluation_complete.result == EvaluationResult.TRUE
