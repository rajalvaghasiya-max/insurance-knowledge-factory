from __future__ import annotations

from insurance_intelligence.contracts.reasoning_plan import build_evidence_requirement
from insurance_intelligence.contracts.topic_completeness import (
    build_component_definition,
    build_topic_definition,
)
from insurance_intelligence.planning.semantic_request_selector import (
    select_requested_semantic_component,
)


def _component(
    component_id: str,
    requirement_type: str,
    *request_terms: str,
):
    return build_component_definition(
        component_id=component_id,
        requirement_type=requirement_type,
        required=True,
        acceptable_requirement_statuses=("SATISFIED",),
        acceptable_evidence_roles=("DEFINING",),
        minimum_authority="AUTHORITATIVE",
        dependency_component_ids=(),
        reason=f"Resolve {component_id}.",
        request_terms=request_terms,
    )


def test_governed_request_terms_select_different_waiting_period_components() -> None:
    definition = build_topic_definition(
        topic_id="waiting_period",
        topic_version="test",
        domain="health",
        components=(
            _component(
                "waiting_period_duration",
                "WAITING_PERIOD_DURATION",
                "waiting period",
                "how long",
                "duration",
            ),
            _component(
                "waiting_period_subject",
                "WAITING_PERIOD_SUBJECT",
                "what does it apply to",
                "subject",
            ),
            _component(
                "start_basis",
                "WAITING_PERIOD_START_BASIS",
                "when does it start",
                "start from",
            ),
        ),
    )

    assert select_requested_semantic_component(
        question="What is the PED waiting period in Star Comprehensive?",
        definition=definition,
    ) == "waiting_period_duration"

    assert select_requested_semantic_component(
        question="When does this waiting period start?",
        definition=definition,
    ) == "start_basis"


def test_selector_is_generic_on_untuned_coverage_limit_topic() -> None:
    definition = build_topic_definition(
        topic_id="coverage_limit",
        topic_version="test",
        domain="health",
        components=(
            _component(
                "limit_value",
                "LIMIT_VALUE",
                "how much",
                "limit",
            ),
            _component(
                "covered_subject",
                "COVERED_SUBJECT",
                "what does it cover",
                "what is limited",
            ),
        ),
    )

    assert select_requested_semantic_component(
        question="How much is the limit?",
        definition=definition,
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
