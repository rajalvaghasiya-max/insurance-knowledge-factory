from dataclasses import replace

from insurance_intelligence.contracts.topic_profile import (
    validate_registered_topic_profile,
)
from insurance_intelligence.topic_completeness.catalogue import (
    build_default_topic_registry,
)
from insurance_intelligence.topic_completeness.star_pilot_profiles import (
    build_star_conditional_copayment_profile,
    build_star_room_rent_profile,
    star_pilot_topic_profiles,
)


def test_star_pilot_profiles_reference_registered_generic_topics():
    registry = build_default_topic_registry()
    profiles = star_pilot_topic_profiles()

    assert tuple(profile.profile_id for profile in profiles) == (
        "star_comprehensive_conditional_copayment",
        "star_comprehensive_room_rent",
    )
    assert tuple(profile.topic_id for profile in profiles) == (
        "conditional_obligation",
        "coverage_limit",
    )

    for profile in profiles:
        assert profile.topic_version == "1.0"
        assert profile.domain == "health"
        result = validate_registered_topic_profile(profile=profile, registry=registry)
        assert result.valid is True
        assert result.failures == ()


def test_star_conditional_copayment_requires_all_material_semantics():
    profile = build_star_conditional_copayment_profile()

    assert profile.required_component_ids == (
        "obligation_value",
        "trigger_condition",
        "applicability_scope",
        "exception_condition",
        "calculation_basis",
    )
    assert profile.optional_component_ids == ()
    assert profile.explanation_blocking_component_ids == profile.required_component_ids


def test_star_room_rent_requires_limit_scope_and_excess_consequence():
    profile = build_star_room_rent_profile()

    assert profile.required_component_ids == (
        "covered_subject",
        "limit_value",
        "limit_basis",
        "applicability_scope",
        "excess_consequence",
    )
    assert profile.optional_component_ids == ()
    assert profile.explanation_blocking_component_ids == profile.required_component_ids


def test_missing_copayment_trigger_exception_scope_or_basis_invalidates_profile():
    registry = build_default_topic_registry()
    profile = build_star_conditional_copayment_profile()

    for component_id in (
        "trigger_condition",
        "exception_condition",
        "applicability_scope",
        "calculation_basis",
    ):
        required = tuple(
            item for item in profile.required_component_ids if item != component_id
        )
        blocking = tuple(
            item
            for item in profile.explanation_blocking_component_ids
            if item != component_id
        )
        mutated = replace(
            profile,
            required_component_ids=required,
            explanation_blocking_component_ids=blocking,
        )
        result = validate_registered_topic_profile(
            profile=mutated,
            registry=registry,
        )
        assert result.valid is False
        assert result.failures


def test_missing_room_rent_limit_scope_or_consequence_invalidates_profile():
    registry = build_default_topic_registry()
    profile = build_star_room_rent_profile()

    for component_id in (
        "limit_value",
        "limit_basis",
        "applicability_scope",
        "excess_consequence",
    ):
        required = tuple(
            item for item in profile.required_component_ids if item != component_id
        )
        blocking = tuple(
            item
            for item in profile.explanation_blocking_component_ids
            if item != component_id
        )
        mutated = replace(
            profile,
            required_component_ids=required,
            explanation_blocking_component_ids=blocking,
        )
        result = validate_registered_topic_profile(
            profile=mutated,
            registry=registry,
        )
        assert result.valid is False
        assert result.failures


def test_star_profiles_are_deterministic():
    assert star_pilot_topic_profiles() == star_pilot_topic_profiles()
