from __future__ import annotations

from dataclasses import replace

import pytest

from insurance_intelligence.authoritative_publication.gate import (
    AuthoritativePublicationGateError,
    create_authoritative_publication,
)
from insurance_intelligence.contracts.authoritative_publication import (
    build_authoritative_publication_input,
    build_governed_publication_projection,
    build_governed_semantic_component,
)
from insurance_intelligence.contracts.publication_decision import PublicationDecisionResult


def decision(**overrides) -> PublicationDecisionResult:
    values = dict(
        contract_version="1.0",
        decision_id="decision-1",
        governed_subject_reference="product:generic:plan-a",
        certification_id="cert-1",
        certification_outcome="PASS",
        topic_id="coverage_limit",
        topic_version="1.0",
        requested_status="PUBLISH",
        decision_status="PUBLISH",
        decision_reasons=("Certified semantics are eligible for publication.",),
        limitations=("This does not guarantee claim payment.",),
        certification_trace_references=("cert-trace-1",),
        evidence_trace_references=("evidence-trace-1",),
        decision_authority="governance-board",
        publication_permitted=True,
        authoritative_publication_created=False,
        failures=(),
    )
    values.update(overrides)
    return PublicationDecisionResult(**values)


def projection(**overrides):
    values = dict(
        projection_id="projection-1",
        governed_subject_reference="product:generic:plan-a",
        certification_id="cert-1",
        topic_id="coverage_limit",
        topic_version="1.0",
        semantic_components=(
            build_governed_semantic_component(
                component_id="limit_value",
                status="SATISFIED",
                evidence_references=("evidence:limit-value",),
            ),
        ),
        limitations=("This does not guarantee claim payment.",),
        evidence_trace_references=("evidence-trace-1",),
        certification_trace_references=("cert-trace-1",),
    )
    values.update(overrides)
    return build_governed_publication_projection(**values)


def publish(*, publication_decision=None, governed_projection=None):
    return create_authoritative_publication(
        build_authoritative_publication_input(
            publication_id="publication-1",
            publication_decision=publication_decision or decision(),
            governed_projection=governed_projection or projection(),
            publication_authority="governance-board",
        )
    )


def test_valid_publish_decision_creates_authoritative_record():
    result = publish()
    assert result.publication_status == "AUTHORITATIVE"
    assert result.decision_id == "decision-1"
    assert result.semantic_components == projection().semantic_components
    assert result.publication_receipt_id.startswith("publication_receipt_")


@pytest.mark.parametrize("status", ["WITHHOLD", "BLOCKED"])
def test_non_publish_decisions_are_rejected(status):
    with pytest.raises(AuthoritativePublicationGateError, match="Only a PUBLISH"):
        publish(
            publication_decision=decision(
                requested_status=status,
                decision_status=status,
                publication_permitted=False,
            )
        )


def test_inconsistent_or_previously_published_decision_is_rejected():
    with pytest.raises(AuthoritativePublicationGateError, match="publication_permitted"):
        publish(publication_decision=decision(publication_permitted=False))
    with pytest.raises(AuthoritativePublicationGateError, match="prior authoritative"):
        publish(publication_decision=decision(authoritative_publication_created=True))


def test_failed_certification_is_rejected():
    with pytest.raises(AuthoritativePublicationGateError, match="must be PASS"):
        publish(publication_decision=decision(certification_outcome="FAIL"))


@pytest.mark.parametrize(
    ("projection_overrides", "message"),
    [
        ({"governed_subject_reference": "product:other:plan"}, "subject"),
        ({"certification_id": "cert-other"}, "Certification ID"),
        ({"topic_id": "waiting_period"}, "Topic ID"),
        ({"topic_version": "2.0"}, "Topic version"),
        ({"limitations": ()}, "limitations"),
        ({"limitations": ("This does not guarantee claim payment.", "Invented limitation.")}, "limitations"),
        ({"certification_trace_references": ("other-cert-trace",)}, "Certification trace"),
        ({"evidence_trace_references": ("other-evidence-trace",)}, "Evidence trace"),
    ],
)
def test_projection_must_exactly_match_decision(projection_overrides, message):
    with pytest.raises(AuthoritativePublicationGateError, match=message):
        publish(governed_projection=projection(**projection_overrides))


def test_bound_not_published_is_rejected():
    limitations = (
        "This rule is bound_not_published pending governance approval.",
    )
    with pytest.raises(AuthoritativePublicationGateError, match="bound_not_published"):
        publish(
            publication_decision=decision(limitations=limitations),
            governed_projection=projection(limitations=limitations),
        )


def test_claim_payment_guarantee_language_is_rejected():
    limitations = ("This publication would guarantee claim payment.",)
    with pytest.raises(AuthoritativePublicationGateError, match="Claim-payment"):
        publish(
            publication_decision=decision(limitations=limitations),
            governed_projection=projection(limitations=limitations),
        )


def test_output_is_deterministic_and_inputs_are_not_mutated():
    item = build_authoritative_publication_input(
        publication_id="publication-1",
        publication_decision=decision(),
        governed_projection=projection(),
        publication_authority="governance-board",
    )
    before = repr(item)
    first = create_authoritative_publication(item)
    second = create_authoritative_publication(item)
    assert first == second
    assert repr(item) == before


def test_non_star_subject_works_without_code_changes():
    subject = "product:other_insurer:plan-b"
    result = publish(
        publication_decision=decision(governed_subject_reference=subject),
        governed_projection=projection(governed_subject_reference=subject),
    )
    assert result.governed_subject_reference == subject


def test_record_contains_no_answer_recommendation_or_claim_decision_fields():
    result = publish()
    for field in (
        "final_answer",
        "explanation",
        "recommendation",
        "medical_suitability",
        "claim_decision",
        "claim_payment",
    ):
        assert not hasattr(result, field)


def test_gate_rejects_unvalidated_input():
    with pytest.raises(AuthoritativePublicationGateError, match="AuthoritativePublicationInput"):
        create_authoritative_publication(object())  # type: ignore[arg-type]
