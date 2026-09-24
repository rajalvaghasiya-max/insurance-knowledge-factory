from __future__ import annotations

from insurance_intelligence.topic_completeness.catalogue import (
    build_coverage_limit_definition,
    build_waiting_period_definition,
)
from insurance_intelligence.topic_completeness.query_selection import (
    select_direct_component,
)


def test_waiting_period_generic_question_defaults_to_duration() -> None:
    definition = build_waiting_period_definition()

    assert (
        select_direct_component(
            definition,
            "What is the PED waiting period in Star Comprehensive?",
        )
        == "waiting_period_duration"
    )


def test_waiting_period_explicit_component_questions_override_default() -> None:
    definition = build_waiting_period_definition()

    assert (
        select_direct_component(
            definition,
            "What does the waiting period apply to?",
        )
        == "waiting_period_subject"
    )
    assert (
        select_direct_component(
            definition,
            "When does the waiting period start?",
        )
        == "start_basis"
    )
    assert (
        select_direct_component(
            definition,
            "Does portability or prior coverage reduce the waiting period?",
        )
        == "continuity_or_credit_rule"
    )


def test_multi_attribute_question_does_not_guess_one_primary_component() -> None:
    definition = build_waiting_period_definition()

    assert (
        select_direct_component(
            definition,
            "How long is the waiting period and when does it start?",
        )
        is None
    )


def test_untuned_coverage_limit_topic_uses_same_generic_selector() -> None:
    definition = build_coverage_limit_definition()

    assert (
        select_direct_component(
            definition,
            "What is the room rent limit?",
        )
        == "limit_value"
    )
    assert (
        select_direct_component(
            definition,
            "What is the basis of this coverage limit?",
        )
        == "limit_basis"
    )
