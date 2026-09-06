from __future__ import annotations

import pytest

from insurance_intelligence.authoritative_publication.gate import (
    create_authoritative_publication,
)
from insurance_intelligence.contracts.authoritative_publication import (
    build_authoritative_publication_input,
    build_governed_publication_projection,
    build_governed_semantic_component,
)
from insurance_intelligence.contracts.publication_decision import (
    PublicationDecisionContractError,
    build_publication_boundary_authorization,
    build_publication_decision_input,
)
from insurance_intelligence.contracts.rule_certification import RuleCertificationResult
from insurance_intelligence.publication_decision.evaluator import (
    evaluate_publication_decision,
)

SUBJECT = "governed_fact:generic:test"
CERTIFICATION_ID = "certification:generic:test"
BOUNDARY_LIMITATION = "The governed binding remains bound_not_published and is used only for internal certification."
SEMANTIC_LIMITATION = "This certification does not determine customer-specific eligibility or claim payment."


def _certification() -> RuleCertificationResult:
    return RuleCertificationResult(
        contract_version="1.0",
        certification_id=CERTIFICATION_ID,
        governed_subject_reference=SUBJECT,
        request_id="request:generic:test",
        resolution_id="resolution:generic:test",
        resolution_status="RESOLVED",
        evidence_sufficiency="COMPLETE",
        topic_id="generic_fact",
        topic_version="1.0",
        expected_completeness_statuses=("COMPLETE",),
        actual_completeness_status="COMPLETE",
        expected_explanation_permitted=True,
        actual_explanation_permitted=True,
        component_checks=(),
        outcome="PASS",
        failures=(),
        limitations=(BOUNDARY_LIMITATION, SEMANTIC_LIMITATION),
        trace_references=("certification-trace:generic:test",),
    )


def _authorization():
    return build_publication_boundary_authorization(
        authorization_id="publication-authorization:generic:test",
        governed_subject_reference=SUBJECT,
        certification_id=CERTIFICATION_ID,
        resolved_boundary_tokens=("bound_not_published",),
        authorization_authority="governed publication boundary authority",
        trace_references=("authorization-trace:generic:test",),
    )


def _decision(*, authorization=None, limitations=(SEMANTIC_LIMITATION,)):
    return evaluate_publication_decision(
        build_publication_decision_input(
            decision_id="publication-decision:generic:test",
            governed_subject_reference=SUBJECT,
            certification_result=_certification(),
            requested_status="PUBLISH",
            decision_reasons=("Explicit governed publication request.",),
            limitations=limitations,
            evidence_trace_references=("evidence:generic:test:fact",),
            decision_authority="governed publication decision authority",
            boundary_authorization=authorization,
        )
    )


def test_bound_not_published_remains_blocked_without_explicit_authorization():
    decision = _decision()

    assert decision.decision_status == "BLOCKED"
    assert decision.publication_permitted is False
    assert not decision.resolved_certification_limitations
    assert decision.authorization_id is None
    assert "Effective certification limitations were not fully preserved." in decision.failures


def test_explicit_authorization_resolves_only_publication_state_boundary():
    decision = _decision(authorization=_authorization())

    assert decision.decision_status == "PUBLISH"
    assert decision.publication_permitted is True
    assert decision.limitations == (SEMANTIC_LIMITATION,)
    assert decision.resolved_certification_limitations == (BOUNDARY_LIMITATION,)
    assert decision.authorization_id == "publication-authorization:generic:test"
    assert decision.authorization_trace_references == ("authorization-trace:generic:test",)


def test_authoritative_publication_preserves_authorization_lineage():
    decision = _decision(authorization=_authorization())
    projection = build_governed_publication_projection(
        projection_id="publication-projection:generic:test",
        governed_subject_reference=SUBJECT,
        certification_id=CERTIFICATION_ID,
        topic_id="generic_fact",
        topic_version="1.0",
        semantic_components=(
            build_governed_semantic_component(
                component_id="fact",
                status="SATISFIED",
                evidence_references=("evidence:generic:test:fact",),
            ),
        ),
        limitations=decision.limitations,
        evidence_trace_references=decision.evidence_trace_references,
        certification_trace_references=decision.certification_trace_references,
    )
    publication = create_authoritative_publication(
        build_authoritative_publication_input(
            publication_id="authoritative-publication:generic:test",
            publication_decision=decision,
            governed_projection=projection,
            publication_authority="governed authoritative publication authority",
        )
    )

    assert publication.publication_status == "AUTHORITATIVE"
    assert publication.resolved_certification_limitations == (BOUNDARY_LIMITATION,)
    assert publication.authorization_id == "publication-authorization:generic:test"
    assert publication.authorization_trace_references == ("authorization-trace:generic:test",)
    assert "bound_not_published" not in " ".join(publication.limitations)


def test_authorization_cannot_resolve_arbitrary_semantic_limitation():
    with pytest.raises(PublicationDecisionContractError, match="unsupported publication boundary"):
        build_publication_boundary_authorization(
            authorization_id="publication-authorization:bad",
            governed_subject_reference=SUBJECT,
            certification_id=CERTIFICATION_ID,
            resolved_boundary_tokens=("claim payment",),
            authorization_authority="governed publication boundary authority",
            trace_references=("authorization-trace:bad",),
        )
