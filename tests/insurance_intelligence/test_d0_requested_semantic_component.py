from __future__ import annotations

from insurance_intelligence.contracts.reasoning_plan import build_evidence_requirement
from insurance_intelligence.planning.semantic_request_selector import (
    select_requested_semantic_component,
)
from insurance_intelligence.topic_completeness.catalogue import (
    build_coverage_limit_definition,
    build_waiting_period_definition,
)


def test_case_a_selects_waiting_period_duration() -> None:
    assert select_requested_semantic_component(
        question="What is the PED waiting period in Star Comprehensive?",
        definition=build_waiting_period_definition(),
    ) == "waiting_period_duration"


def test_explicit_start_question_overrides_generic_waiting_period_language() -> None:
    assert select_requested_semantic_component(
        question="When does this waiting period start?",
        definition=build_waiting_period_definition(),
    ) == "start_basis"


def test_selector_is_generic_on_coverage_limit_topic() -> None:
    assert select_requested_semantic_component(
        question="How much is the limit?",
        definition=build_coverage_limit_definition(),
    ) == "limit_value"


def test_evidence_requirement_carries_requested_semantic_component() -> None:
    requirement = build_evidence_requirement(
        requirement_id="evreq-1",
        evidence_category="NORMALIZED_PRODUCT_FACT",
        subject_reference="product:test",
        required=True,
        authority_requirement="AUTHORITATIVE",
        version_requirement="CURRENT_APPLICABLE",
        reason="Resolve the requested product fact.",
        requested_by_step="step-1",
        requested_semantic_component="waiting_period_duration",
    )
    assert requirement.requested_semantic_component == "waiting_period_duration"
