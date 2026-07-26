from __future__ import annotations

import pytest

from insurance_intelligence.evaluation.scenarios import (
    EvaluationScenarioRegistry,
    EvaluationScenarioRegistryError,
    build_default_registry,
    default_scenarios,
)


def test_default_catalog_contains_expected_scenarios():
    ids = {item.scenario_id for item in default_scenarios()}
    assert ids == {
        "star_copay_general_explanation",
        "star_copay_missing_trigger",
        "star_copay_trigger_confirmed",
        "star_copay_trigger_disproved",
        "star_copay_failed_lineage",
        "star_copay_version_unresolved",
        "star_copay_material_conflict",
        "unsupported_product_recommendation",
        "star_copay_customer_format",
        "star_copay_advisor_format",
        "star_copay_determinism",
    }


def test_default_catalog_order_is_deterministic():
    first = tuple(item.scenario_id for item in default_scenarios())
    second = tuple(item.scenario_id for item in default_scenarios())
    assert first == second


def test_registry_orders_by_priority_then_id():
    registry = build_default_registry()
    priorities = tuple(item.priority for item in registry.all_scenarios())
    assert priorities == tuple(sorted(priorities))


def test_registry_rejects_duplicate_registration():
    scenario = default_scenarios()[0]
    registry = EvaluationScenarioRegistry((scenario,))
    with pytest.raises(EvaluationScenarioRegistryError):
        registry.register(scenario)


def test_registry_rejects_ambiguous_id_across_versions():
    scenario = default_scenarios()[0]
    other = scenario.__class__(**{**scenario.__dict__, "scenario_version": "2.0"})
    registry = EvaluationScenarioRegistry((scenario,))
    with pytest.raises(EvaluationScenarioRegistryError):
        registry.register(other)


def test_registry_get_returns_exact_scenario():
    registry = build_default_registry()
    result = registry.get("star_copay_failed_lineage")
    assert result.expected_response_statuses == ("INSUFFICIENT_EVIDENCE", "BLOCKED")


def test_registry_get_unknown_fails_closed():
    with pytest.raises(EvaluationScenarioRegistryError):
        build_default_registry().get("missing")


def test_select_by_kind():
    selected = build_default_registry().select(scenario_kind="FAILURE_STATE")
    assert {item.scenario_id for item in selected} == {
        "star_copay_failed_lineage",
        "star_copay_version_unresolved",
        "star_copay_material_conflict",
    }


def test_select_by_tags():
    selected = build_default_registry().select(tags=("star_comprehensive", "copayment"))
    assert len(selected) == 11


def test_general_scenario_preserves_percentage_and_condition():
    scenario = build_default_registry().get("star_copay_general_explanation")
    assert "preserve_percentage" in scenario.required_behaviors
    assert "preserve_condition" in scenario.required_behaviors
    assert "recommend_product" in scenario.prohibited_behaviors


def test_missing_trigger_requires_clarification_behavior():
    scenario = build_default_registry().get("star_copay_missing_trigger")
    assert scenario.expected_response_statuses == ("CLARIFICATION_REQUIRED",)
    assert "request_trigger_context" in scenario.required_behaviors
    assert "state_trigger_applies" in scenario.prohibited_behaviors


def test_failed_lineage_fails_closed():
    scenario = build_default_registry().get("star_copay_failed_lineage")
    assert scenario.input_context["fixture_state"] == "FAILED_LINEAGE"
    assert "fail_closed" in scenario.required_behaviors
    assert "emit_answer" in scenario.prohibited_behaviors


def test_unsupported_recommendation_is_not_answered():
    scenario = build_default_registry().get("unsupported_product_recommendation")
    assert set(scenario.expected_response_statuses) == {"UNSUPPORTED", "BLOCKED"}
    assert "recommend_product" in scenario.prohibited_behaviors


def test_customer_and_advisor_scenarios_are_distinct():
    registry = build_default_registry()
    customer = registry.get("star_copay_customer_format")
    advisor = registry.get("star_copay_advisor_format")
    assert customer.audience == "CUSTOMER"
    assert advisor.audience == "ADVISOR"


def test_determinism_scenario_declares_stable_outputs():
    scenario = build_default_registry().get("star_copay_determinism")
    assert scenario.scenario_kind == "DETERMINISM"
    assert {
        "identical_response_id",
        "identical_section_order",
        "identical_trace_order",
    }.issubset(set(scenario.required_behaviors))
