from dataclasses import FrozenInstanceError, replace

import pytest

from insurance_intelligence.contracts.topic_profile import (
    SUPPORTED_PROFILE_CONTRACT_VERSION,
    TopicProfileContractError,
    build_topic_profile,
    validate_registered_topic_profile,
)
from insurance_intelligence.topic_completeness.catalogue import (
    build_conditional_obligation_definition,
    build_default_topic_registry,
)


def _complete_profile():
    definition = build_conditional_obligation_definition()
    return build_topic_profile(
        profile_id="generic_conditional_obligation_strict",
        profile_version="1.0",
        definition=definition,
        required_component_ids=(
            "obligation_value",
            "trigger_condition",
            "applicability_scope",
            "exception_condition",
            "calculation_basis",
        ),
    )


def test_topic_profile_is_versioned_immutable_and_product_agnostic():
    profile = _complete_profile()

    assert profile.contract_version == SUPPORTED_PROFILE_CONTRACT_VERSION
    assert profile.topic_id == "conditional_obligation"
    assert profile.topic_version == "1.0"
    assert profile.domain == "health"
    assert "star" not in repr(profile).lower()

    with pytest.raises(FrozenInstanceError):
        profile.profile_id = "changed"


def test_topic_profile_must_classify_every_registered_component():
    definition = build_conditional_obligation_definition()

    with pytest.raises(TopicProfileContractError, match="omitted"):
        build_topic_profile(
            profile_id="incomplete",
            profile_version="1.0",
            definition=definition,
            required_component_ids=(
                "obligation_value",
                "trigger_condition",
                "applicability_scope",
            ),
        )


def test_topic_profile_rejects_unknown_duplicate_and_overlapping_components():
    definition = build_conditional_obligation_definition()

    with pytest.raises(TopicProfileContractError, match="unknown"):
        build_topic_profile(
            profile_id="unknown",
            profile_version="1.0",
            definition=definition,
            required_component_ids=(
                "obligation_value",
                "trigger_condition",
                "applicability_scope",
                "exception_condition",
                "calculation_basis",
                "invented_component",
            ),
        )

    with pytest.raises(TopicProfileContractError, match="unique"):
        build_topic_profile(
            profile_id="duplicate",
            profile_version="1.0",
            definition=definition,
            required_component_ids=(
                "obligation_value",
                "obligation_value",
                "trigger_condition",
                "applicability_scope",
                "exception_condition",
                "calculation_basis",
            ),
        )

    with pytest.raises(TopicProfileContractError, match="overlap"):
        build_topic_profile(
            profile_id="overlap",
            profile_version="1.0",
            definition=definition,
            required_component_ids=(
                "obligation_value",
                "trigger_condition",
                "applicability_scope",
                "exception_condition",
            ),
            optional_component_ids=("exception_condition", "calculation_basis"),
        )


def test_topic_profile_cannot_weaken_catalogue_required_components():
    definition = build_conditional_obligation_definition()

    with pytest.raises(TopicProfileContractError, match="cannot weaken"):
        build_topic_profile(
            profile_id="weakened",
            profile_version="1.0",
            definition=definition,
            required_component_ids=(
                "obligation_value",
                "trigger_condition",
                "exception_condition",
                "calculation_basis",
            ),
            optional_component_ids=("applicability_scope",),
        )


def test_explanation_blockers_must_be_required_components():
    definition = build_conditional_obligation_definition()

    with pytest.raises(TopicProfileContractError, match="must be required"):
        build_topic_profile(
            profile_id="invalid_blocker",
            profile_version="1.0",
            definition=definition,
            required_component_ids=(
                "obligation_value",
                "trigger_condition",
                "applicability_scope",
            ),
            optional_component_ids=("exception_condition", "calculation_basis"),
            explanation_blocking_component_ids=(
                "obligation_value",
                "exception_condition",
            ),
        )


def test_registered_profile_validation_is_deterministic_and_exact_versioned():
    profile = _complete_profile()
    registry = build_default_topic_registry()

    first = validate_registered_topic_profile(profile=profile, registry=registry)
    second = validate_registered_topic_profile(profile=profile, registry=registry)

    assert first == second
    assert first.valid is True
    assert first.failures == ()

    wrong_version = replace(profile, topic_version="9.9")
    result = validate_registered_topic_profile(
        profile=wrong_version,
        registry=registry,
    )
    assert result.valid is False
    assert "Registered topic not found" in result.failures[0]


def test_registered_profile_validation_detects_mutated_component_classification():
    profile = _complete_profile()
    mutated = replace(
        profile,
        required_component_ids=(
            "obligation_value",
            "trigger_condition",
            "applicability_scope",
            "exception_condition",
        ),
        optional_component_ids=(),
        explanation_blocking_component_ids=(
            "obligation_value",
            "trigger_condition",
            "applicability_scope",
            "exception_condition",
        ),
    )

    result = validate_registered_topic_profile(
        profile=mutated,
        registry=build_default_topic_registry(),
    )

    assert result.valid is False
    assert "component classification" in result.failures[0]
