from __future__ import annotations

from insurance_intelligence.contracts.reasoning_plan import (
    EXECUTION_MODES,
    EXPECTED_OUTCOME_TYPES,
    PLAN_TYPES,
    STEP_TYPES,
)
from insurance_intelligence.intent.taxonomy import GOVERNED_INTENT_LABELS
from insurance_intelligence.planning.registry import (
    DEFAULT_STEPS_BY_PLAN_TYPE,
    INTENT_TO_PLAN_TYPE,
    PLAN_TYPE_DEFINITIONS,
    PLAN_TYPE_TO_EXECUTION_MODE,
    PLAN_TYPE_TO_EXPECTED_OUTCOME,
    STEP_REGISTRY,
)


def test_plan_type_definitions_cover_all_governed_plan_types():
    assert set(PLAN_TYPE_DEFINITIONS) == PLAN_TYPES


def test_step_registry_covers_all_governed_step_types():
    assert set(STEP_REGISTRY) == STEP_TYPES


def test_every_intent_maps_to_a_governed_plan_type():
    assert set(INTENT_TO_PLAN_TYPE) == GOVERNED_INTENT_LABELS
    assert set(INTENT_TO_PLAN_TYPE.values()) <= PLAN_TYPES


def test_recommendation_maps_to_recommendation_plan():
    assert INTENT_TO_PLAN_TYPE["RECOMMENDATION"] == "RECOMMENDATION_PLAN"


def test_product_comparison_maps_to_comparison_plan():
    assert INTENT_TO_PLAN_TYPE["PRODUCT_COMPARISON"] == "COMPARISON_PLAN"


def test_every_plan_type_has_an_execution_mode():
    assert set(PLAN_TYPE_TO_EXECUTION_MODE) == PLAN_TYPES
    assert set(PLAN_TYPE_TO_EXECUTION_MODE.values()) <= EXECUTION_MODES


def test_every_plan_type_has_a_default_template():
    assert set(DEFAULT_STEPS_BY_PLAN_TYPE) == PLAN_TYPES
    for plan_type, steps in DEFAULT_STEPS_BY_PLAN_TYPE.items():
        assert len(steps) > 0
        assert set(steps) <= STEP_TYPES


def test_every_plan_type_has_an_expected_outcome():
    assert set(PLAN_TYPE_TO_EXPECTED_OUTCOME) == PLAN_TYPES
    assert set(PLAN_TYPE_TO_EXPECTED_OUTCOME.values()) <= EXPECTED_OUTCOME_TYPES


def test_comparison_plan_template_does_not_include_recommendation_step():
    assert "FORM_CONDITIONAL_RECOMMENDATION" not in DEFAULT_STEPS_BY_PLAN_TYPE["COMPARISON_PLAN"]


def test_recommendation_plan_template_includes_safety_gate():
    assert "APPLY_SAFETY_GATE" in DEFAULT_STEPS_BY_PLAN_TYPE["RECOMMENDATION_PLAN"]
    assert "FORM_CONDITIONAL_RECOMMENDATION" in DEFAULT_STEPS_BY_PLAN_TYPE["RECOMMENDATION_PLAN"]


def test_direct_fact_plan_template_has_no_recommendation_or_comparison_steps():
    steps = DEFAULT_STEPS_BY_PLAN_TYPE["DIRECT_FACT_PLAN"]
    assert "FORM_CONDITIONAL_RECOMMENDATION" not in steps
    assert "COMPARE_OPTIONS" not in steps


def test_step_definitions_are_internally_consistent():
    for step_type, definition in STEP_REGISTRY.items():
        assert definition.step_type == step_type
        assert definition.allowed_plan_types <= PLAN_TYPES
        assert definition.risk_level in {"low", "medium", "high"}
