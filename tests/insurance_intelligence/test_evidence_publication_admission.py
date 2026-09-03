from pathlib import Path

import pytest

from insurance_intelligence.authoritative_publication.gate import (
    AuthoritativePublicationGateError,
)
from insurance_intelligence.authoritative_publication.star_health import (
    build_star_conditional_copayment_authoritative_publication,
    build_star_room_rent_authoritative_publication,
)
from insurance_intelligence.contracts.evidence import build_input as build_evidence_input
from insurance_intelligence.contracts.reasoning_plan import (
    build_evidence_requirement,
    build_plan,
)
from insurance_intelligence.evidence.admission import (
    EvidenceAdmissionError,
    INTERNAL_CERTIFICATION,
    USER_ANSWER,
    evaluate_publication_admission,
)
from insurance_intelligence.evidence.resolver import EvidenceResolver
from insurance_intelligence.publication_decision.star_health import (
    build_star_conditional_copayment_publication_decision,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "knowledge" / "factory" / "registry_backed"


def _plan():
    requirement = build_evidence_requirement(
        requirement_id="req_copay",
        evidence_category="NORMALIZED_PRODUCT_FACT",
        subject_reference="star_health:star_comprehensive",
        required=True,
        authority_requirement="BINDING",
        version_requirement="ANY_GOVERNED",
        reason="resolve conditional copay evidence",
        requested_by_step="step_1",
    )
    return build_plan(
        request_id="req-publication-admission",
        plan_id="plan-publication-admission",
        plan_type="CLAUSE_IMPACT_PLAN",
        execution_mode="INTERPRETIVE",
        goal="resolve evidence",
        expected_outcome="CLAUSE_IMPACT_EXPLANATION",
        plan_status="READY",
        confidence=0.9,
        required_evidence=(requirement,),
    )


def _resolve(*, evidence_use: str, publication_lookup=None):
    return EvidenceResolver(publication_lookup=publication_lookup).resolve(
        build_evidence_input(
            request_id="req-publication-admission",
            reasoning_plan=_plan(),
            resolution_context={"evidence_use": evidence_use},
            repository_roots=(str(REGISTRY),),
            strict_mode="STRICT",
        )
    )


def test_internal_certification_keeps_historical_governed_binding_access():
    result = _resolve(evidence_use=INTERNAL_CERTIFICATION)

    assert result.resolution_status == "RESOLVED"
    assert result.sufficiency == "COMPLETE"
    assert len(result.evidence_packages) == 1


def test_user_answer_without_authoritative_publication_fails_closed():
    result = _resolve(evidence_use=USER_ANSWER)

    assert result.resolution_status == "NOT_RESOLVED"
    assert result.sufficiency == "MISSING"
    assert result.evidence_packages == ()
    assert result.requirement_results[0].status == "MISSING"
    assert "authoritative publication" in result.requirement_results[0].missing_reason
    assert any("authoritative publication" in item for item in result.limitations)


def test_published_room_rent_record_is_valid_positive_admission_control():
    publication = build_star_room_rent_authoritative_publication()

    decision = evaluate_publication_admission(
        evidence_use=USER_ANSWER,
        publication=publication,
        topic_id=publication.topic_id,
    )

    assert decision.admitted is True
    assert decision.publication_id == publication.publication_id
    assert decision.publication_receipt_id == publication.publication_receipt_id


def test_wrong_published_topic_does_not_admit_copay_answer_evidence():
    publication = build_star_room_rent_authoritative_publication()

    result = _resolve(
        evidence_use=USER_ANSWER,
        publication_lookup=lambda _entity, _topic: publication,
    )

    assert result.resolution_status == "NOT_RESOLVED"
    assert result.evidence_packages == ()
    assert "topic does not match" in result.requirement_results[0].missing_reason


def test_withheld_copay_cannot_create_authoritative_publication_or_answer_admission():
    decision = build_star_conditional_copayment_publication_decision()

    assert decision.decision_status == "WITHHOLD"
    assert decision.publication_permitted is False
    with pytest.raises(AuthoritativePublicationGateError):
        build_star_conditional_copayment_authoritative_publication()

    admission = evaluate_publication_admission(
        evidence_use=USER_ANSWER,
        publication=None,
        topic_id="conditional_copayment",
    )
    assert admission.admitted is False


def test_invalid_evidence_use_fails_closed():
    with pytest.raises(EvidenceAdmissionError):
        _resolve(evidence_use="UNREVIEWED_RUNTIME")
