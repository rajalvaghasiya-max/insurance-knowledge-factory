"""Star Comprehensive pilot profiles built on generic topic-profile contracts."""

from __future__ import annotations

from insurance_intelligence.contracts.topic_profile import TopicProfile, build_topic_profile
from insurance_intelligence.topic_completeness.catalogue import (
    build_conditional_obligation_definition,
    build_coverage_limit_definition,
)

PROFILE_VERSION = "1.0"


def build_star_conditional_copayment_profile() -> TopicProfile:
    definition = build_conditional_obligation_definition()
    return build_topic_profile(
        profile_id="star_comprehensive_conditional_copayment",
        profile_version=PROFILE_VERSION,
        definition=definition,
        required_component_ids=(
            "obligation_value",
            "trigger_condition",
            "applicability_scope",
            "exception_condition",
            "calculation_basis",
        ),
        optional_component_ids=(),
        explanation_blocking_component_ids=(
            "obligation_value",
            "trigger_condition",
            "applicability_scope",
            "exception_condition",
            "calculation_basis",
        ),
    )


def build_star_room_rent_profile() -> TopicProfile:
    definition = build_coverage_limit_definition()
    return build_topic_profile(
        profile_id="star_comprehensive_room_rent",
        profile_version=PROFILE_VERSION,
        definition=definition,
        required_component_ids=(
            "covered_subject",
            "limit_value",
            "limit_basis",
            "applicability_scope",
            "excess_consequence",
        ),
        optional_component_ids=(),
        explanation_blocking_component_ids=(
            "covered_subject",
            "limit_value",
            "limit_basis",
            "applicability_scope",
            "excess_consequence",
        ),
    )


def star_pilot_topic_profiles() -> tuple[TopicProfile, ...]:
    return (
        build_star_conditional_copayment_profile(),
        build_star_room_rent_profile(),
    )
