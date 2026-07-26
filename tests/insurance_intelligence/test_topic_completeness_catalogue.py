from __future__ import annotations

from insurance_intelligence.topic_completeness.catalogue import (
    CATALOGUE_VERSION,
    build_conditional_obligation_definition,
    build_coverage_limit_definition,
    build_default_topic_registry,
    build_eligibility_and_consequence_definition,
    build_waiting_period_definition,
    default_topic_definitions,
)


def _component_map(definition):
    return {component.component_id: component for component in definition.components}


def test_default_catalogue_contains_four_materially_different_topics():
    definitions = default_topic_definitions()

    assert tuple(item.topic_id for item in definitions) == (
        "conditional_obligation",
        "coverage_limit",
        "eligibility_and_consequence",
        "waiting_period",
    )
    assert all(item.topic_version == CATALOGUE_VERSION for item in definitions)
    assert all(item.domain == "health" for item in definitions)


def test_conditional_obligation_has_required_trigger_value_and_scope():
    definition = build_conditional_obligation_definition()
    components = _component_map(definition)

    assert {component_id for component_id, component in components.items() if component.required} == {
        "obligation_value",
        "trigger_condition",
        "applicability_scope",
    }
    assert components["exception_condition"].dependency_component_ids == (
        "trigger_condition",
    )
    assert components["calculation_basis"].dependency_component_ids == (
        "obligation_value",
    )


def test_eligibility_topic_requires_both_positive_and_negative_consequences():
    definition = build_eligibility_and_consequence_definition()
    components = _component_map(definition)

    assert components["eligible_consequence"].required is True
    assert components["ineligible_consequence"].required is True
    assert components["eligible_consequence"].dependency_component_ids == (
        "eligibility_criteria",
    )
    assert components["ineligible_consequence"].dependency_component_ids == (
        "eligibility_criteria",
    )


def test_coverage_limit_topic_models_basis_and_excess_consequence():
    definition = build_coverage_limit_definition()
    components = _component_map(definition)

    assert components["limit_value"].required is True
    assert components["limit_basis"].required is True
    assert components["limit_basis"].dependency_component_ids == ("limit_value",)
    assert components["excess_consequence"].required is False
    assert components["excess_consequence"].dependency_component_ids == (
        "limit_value",
        "limit_basis",
    )


def test_waiting_period_topic_models_duration_subject_and_start_basis():
    definition = build_waiting_period_definition()
    components = _component_map(definition)

    required_ids = {
        component_id
        for component_id, component in components.items()
        if component.required
    }
    assert required_ids == {
        "waiting_period_duration",
        "waiting_period_subject",
        "start_basis",
        "applicability_scope",
    }
    assert components["continuity_or_credit_rule"].dependency_component_ids == (
        "waiting_period_duration",
        "start_basis",
    )


def test_default_registry_registers_and_activates_every_topic():
    registry = build_default_topic_registry()

    for definition in default_topic_definitions():
        assert registry.contains(
            topic_id=definition.topic_id,
            topic_version=definition.topic_version,
        )
        assert registry.active_version(definition.topic_id) == CATALOGUE_VERSION
        assert registry.get(definition.topic_id) == definition


def test_default_registry_builder_returns_independent_registries():
    first = build_default_topic_registry()
    second = build_default_topic_registry()

    assert first is not second
    assert first.all_definitions() == second.all_definitions()


def test_catalogue_order_is_deterministic():
    assert default_topic_definitions() == default_topic_definitions()
    assert default_topic_definitions() == build_default_topic_registry().all_definitions()


def test_catalogue_has_no_insurer_product_plan_uin_or_document_identifiers():
    forbidden_fragments = (
        "star",
        "aditya",
        "bajaj",
        "insurer",
        "product",
        "plan_",
        "uin",
        "document_id",
    )

    for definition in default_topic_definitions():
        searchable = " ".join(
            (
                definition.topic_id,
                definition.topic_version,
                *(component.component_id for component in definition.components),
                *(component.requirement_type for component in definition.components),
            )
        ).lower()
        assert not any(fragment in searchable for fragment in forbidden_fragments)


def test_topics_use_distinct_component_shapes_with_same_contract():
    shapes = {
        definition.topic_id: tuple(
            component.component_id for component in definition.components
        )
        for definition in default_topic_definitions()
    }

    assert len(set(shapes.values())) == 4
    assert "trigger_condition" in shapes["conditional_obligation"]
    assert "limit_basis" in shapes["coverage_limit"]
    assert "ineligible_consequence" in shapes["eligibility_and_consequence"]
    assert "waiting_period_duration" in shapes["waiting_period"]


def test_all_catalogue_components_use_generic_governed_authority():
    for definition in default_topic_definitions():
        assert all(
            component.minimum_authority == "AUTHORITATIVE"
            for component in definition.components
        )


def test_all_required_component_counts_match_contract_invariant():
    for definition in default_topic_definitions():
        required_count = sum(
            component.required for component in definition.components
        )
        assert definition.minimum_required_components == required_count
