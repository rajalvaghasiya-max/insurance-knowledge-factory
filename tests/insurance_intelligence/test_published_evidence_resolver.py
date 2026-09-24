from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from insurance_intelligence.contracts.evidence import build_input
from insurance_intelligence.contracts.reasoning_plan import build_evidence_requirement, build_plan
from insurance_intelligence.coverage_registry.health_seed import HEALTH_COVERAGE_REGISTRY
from insurance_intelligence.evidence.coverage_registry_source import (
    build_coverage_registry_published_source_lookup,
)
from insurance_intelligence.evidence.published_materialization import (
    PublishedEvidenceMaterializationError,
    PublishedEvidenceSource,
    materialize_published_requirement,
)
from insurance_intelligence.evidence.published_resolver import PublishedEvidenceResolver

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "knowledge/factory/registry_backed"
LOOKUP = build_coverage_registry_published_source_lookup(
    registry=HEALTH_COVERAGE_REGISTRY,
    repository_root=ROOT,
)


def _plan(*, reason: str, request_id: str = "req-published"):
    requirement = build_evidence_requirement(
        requirement_id="req_fact",
        evidence_category="NORMALIZED_PRODUCT_FACT",
        subject_reference="star_health:star_comprehensive",
        required=True,
        authority_requirement="AUTHORITATIVE",
        version_requirement="CURRENT_APPLICABLE",
        reason=reason,
        requested_by_step="step_1",
    )
    return build_plan(
        request_id=request_id,
        plan_id="plan-published",
        plan_type="DIRECT_FACT_PLAN",
        execution_mode="DIRECT_GROUNDED",
        goal="resolve published product fact",
        expected_outcome="DIRECT_FACT_RESPONSE",
        plan_status="READY",
        confidence=1.0,
        required_evidence=(requirement,),
    )


def _resolve(reason: str):
    plan = _plan(reason=reason)
    resolver = PublishedEvidenceResolver(LOOKUP)
    return resolver.resolve(
        build_input(
            request_id=plan.request_id,
            reasoning_plan=plan,
            resolution_context={"evidence_use": "USER_ANSWER"},
            repository_roots=(str(REGISTRY),),
            strict_mode="STRICT",
        )
    )


def _answer_role(package):
    values = [
        item.value
        for item in package.semantic_attributes
        if item.key == "answer_role"
    ]
    assert len(values) <= 1
    return values[0] if values else None


def test_room_rent_user_answer_materializes_only_authoritatively_published_evidence():
    out = _resolve("Explain the room rent or room category limit for Star Comprehensive")

    assert out.resolution_status == "RESOLVED"
    assert out.sufficiency == "COMPLETE"
    assert len(out.evidence_packages) == 5
    assert {item.page for item in out.evidence_packages} == {9}
    assert all(item.requirement_id == "req_fact" for item in out.evidence_packages)
    assert all("authoritative_publication_admission" in item.retrieval_basis for item in out.evidence_packages)
    assert all(any(token.startswith("publication_receipt_") for token in item.retrieval_basis) for item in out.evidence_packages)


def test_bariatric_user_answer_materializes_published_evidence_without_core_topic_switch():
    out = _resolve("What are the bariatric surgery eligibility conditions?")

    assert out.resolution_status == "RESOLVED"
    assert out.sufficiency == "COMPLETE"
    assert len(out.evidence_packages) == 5
    assert {item.page for item in out.evidence_packages} == {15}
    assert {item.field_or_topic for item in out.evidence_packages} >= {
        "ELIGIBILITY_CRITERIA",
        "ELIGIBLE_CONSEQUENCE",
        "INELIGIBLE_CONSEQUENCE",
    }


def test_waiting_period_is_answer_admissible_after_authoritative_publication_is_frozen():
    out = _resolve("What is the PED waiting period in Star Comprehensive?")

    assert out.resolution_status == "RESOLVED"
    assert out.sufficiency == "COMPLETE"
    assert out.evidence_packages
    fields = {item.field_or_topic for item in out.evidence_packages}
    assert "WAITING_PERIOD_DURATION" in fields
    assert "CONTINUITY_OR_CREDIT_RULE" in fields
    assert all("authoritative_publication_admission" in item.retrieval_basis for item in out.evidence_packages)


def test_symbolic_semantic_subject_reuses_one_unambiguous_governed_instance_identity():
    plan = _plan(reason="Required to resolve the requested governed product fact")
    requirement = replace(plan.required_evidence[0], subject_reference="term_or_concept")
    plan = replace(
        plan,
        goal="Address a TERM_EXPLANATION request: What is the PED waiting period in Star Comprehensive?",
        required_evidence=(requirement,),
    )
    out = PublishedEvidenceResolver(LOOKUP).resolve(
        build_input(
            request_id=plan.request_id,
            reasoning_plan=plan,
            resolution_context={
                "evidence_use": "USER_ANSWER",
                "resolved_candidate_references": {
                    "product_reference": "star_health:star_comprehensive",
                },
            },
            repository_roots=(str(REGISTRY),),
            strict_mode="STRICT",
        )
    )

    assert out.resolution_status == "RESOLVED"
    assert out.sufficiency == "COMPLETE"
    assert out.entity_resolutions[0].governed_reference == "star_health:star_comprehensive"
    fields = {item.field_or_topic for item in out.evidence_packages}
    assert "WAITING_PERIOD_DURATION" in fields
    assert "CONTINUITY_OR_CREDIT_RULE" in fields


def test_resolved_semantic_context_is_preserved_separately_from_instance_identity():
    plan = _plan(reason="Required to resolve the requested governed product fact")
    requirement = replace(plan.required_evidence[0], subject_reference="term_or_concept")
    plan = replace(
        plan,
        goal="Address a TERM_EXPLANATION request: What is the PED waiting period in Star Comprehensive?",
        required_evidence=(requirement,),
    )
    out = PublishedEvidenceResolver(LOOKUP).resolve(
        build_input(
            request_id=plan.request_id,
            reasoning_plan=plan,
            resolution_context={
                "evidence_use": "USER_ANSWER",
                "resolved_context_values": {"term_or_concept": "waiting period"},
                "resolved_candidate_references": {
                    "product_reference": "star_health:star_comprehensive",
                },
            },
            repository_roots=(str(REGISTRY),),
            strict_mode="STRICT",
        )
    )

    assert out.resolution_status == "RESOLVED"
    assert out.evidence_packages
    assert {item.subject_reference for item in out.evidence_packages} == {"waiting period"}
    assert out.entity_resolutions[0].governed_reference == "star_health:star_comprehensive"


def test_symbolic_subject_with_multiple_candidate_identities_fails_closed():
    plan = _plan(reason="Required to resolve the requested governed product fact")
    requirement = replace(plan.required_evidence[0], subject_reference="term_or_concept")
    plan = replace(
        plan,
        goal="Address a TERM_EXPLANATION request: explain the waiting period",
        required_evidence=(requirement,),
    )
    out = PublishedEvidenceResolver(LOOKUP).resolve(
        build_input(
            request_id=plan.request_id,
            reasoning_plan=plan,
            resolution_context={
                "evidence_use": "USER_ANSWER",
                "resolved_candidate_references": {
                    "product_reference": "star_health:star_comprehensive",
                    "comparison_subject_1": "other_health:other_product",
                },
            },
            repository_roots=(str(REGISTRY),),
            strict_mode="STRICT",
        )
    )

    assert out.sufficiency == "ENTITY_UNRESOLVED"
    assert out.resolution_status != "RESOLVED"
    assert not out.evidence_packages


def test_unknown_product_fails_before_publication_materialization():
    plan = _plan(reason="Explain room rent")
    requirement = replace(plan.required_evidence[0], subject_reference="unknown:product")
    plan = replace(plan, required_evidence=(requirement,))
    out = PublishedEvidenceResolver(LOOKUP).resolve(
        build_input(
            request_id=plan.request_id,
            reasoning_plan=plan,
            resolution_context={"evidence_use": "USER_ANSWER"},
            repository_roots=(str(REGISTRY),),
        )
    )

    assert out.sufficiency == "ENTITY_UNRESOLVED"
    assert not out.evidence_packages


def test_materializer_rejects_publication_reference_missing_from_certified_evidence():
    requirement = _plan(reason="Explain room rent").required_evidence[0]
    source = LOOKUP("star_health:star_comprehensive", requirement)
    assert source is not None
    first_component = source.publication.semantic_components[0]
    bad_component = replace(first_component, evidence_references=("evidence:missing",))
    bad_publication = replace(
        source.publication,
        semantic_components=(bad_component,) + source.publication.semantic_components[1:],
    )

    with pytest.raises(PublishedEvidenceMaterializationError, match="references missing evidence"):
        materialize_published_requirement(
            source=PublishedEvidenceSource(
                publication=bad_publication,
                certified_evidence=source.certified_evidence,
            ),
            requirement_id="req_fact",
            subject_reference="star_health:star_comprehensive",
        )


def test_published_resolver_refuses_internal_certification_mode():
    plan = _plan(reason="Explain room rent")
    with pytest.raises(ValueError, match="requires evidence_use=USER_ANSWER"):
        PublishedEvidenceResolver(LOOKUP).resolve(
            build_input(
                request_id=plan.request_id,
                reasoning_plan=plan,
                resolution_context={"evidence_use": "INTERNAL_CERTIFICATION"},
                repository_roots=(str(REGISTRY),),
            )
        )


def test_waiting_period_requested_outcome_marks_duration_primary() -> None:
    plan = _plan(reason="What is the PED waiting period in Star Comprehensive?")
    out = PublishedEvidenceResolver(LOOKUP).resolve(
        build_input(
            request_id=plan.request_id,
            reasoning_plan=plan,
            resolution_context={
                "evidence_use": "USER_ANSWER",
                "requested_outcome": "What is the PED waiting period in Star Comprehensive?",
            },
            repository_roots=(str(REGISTRY),),
            strict_mode="STRICT",
        )
    )

    roles = {item.field_or_topic: _answer_role(item) for item in out.evidence_packages}
    assert roles["WAITING_PERIOD_DURATION"] == "PRIMARY"
    assert roles["CONTINUITY_OR_CREDIT_RULE"] == "QUALIFYING"


def test_waiting_period_requested_outcome_can_select_optional_continuity_fact() -> None:
    plan = _plan(reason="Does portability reduce the PED waiting period?")
    out = PublishedEvidenceResolver(LOOKUP).resolve(
        build_input(
            request_id=plan.request_id,
            reasoning_plan=plan,
            resolution_context={
                "evidence_use": "USER_ANSWER",
                "requested_outcome": (
                    "Does portability or prior coverage reduce the waiting period?"
                ),
            },
            repository_roots=(str(REGISTRY),),
            strict_mode="STRICT",
        )
    )

    roles = {item.field_or_topic: _answer_role(item) for item in out.evidence_packages}
    assert roles["CONTINUITY_OR_CREDIT_RULE"] == "PRIMARY"
    assert roles["WAITING_PERIOD_DURATION"] is None


def test_waiting_period_ambiguous_requested_outcome_does_not_invent_primary() -> None:
    plan = _plan(reason="How long is the waiting period and does portability reduce it?")
    out = PublishedEvidenceResolver(LOOKUP).resolve(
        build_input(
            request_id=plan.request_id,
            reasoning_plan=plan,
            resolution_context={
                "evidence_use": "USER_ANSWER",
                "requested_outcome": (
                    "How long is the waiting period and does portability reduce it?"
                ),
            },
            repository_roots=(str(REGISTRY),),
            strict_mode="STRICT",
        )
    )

    assert all(_answer_role(item) is None for item in out.evidence_packages)

