from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from insurance_intelligence.contracts.publication_decision import (
    PublicationDecisionContractError,
    build_publication_decision_input,
)
from insurance_intelligence.rule_certification.runner import run_rule_certification
from insurance_intelligence.rule_certification.star_health_room_rent import (
    build_star_comprehensive_room_rent_case,
)


def certification():
    case = build_star_comprehensive_room_rent_case()
    return run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
        trace_references=("certification-trace-1",),
    )


def build_input(**overrides):
    result = certification()
    values = dict(
        decision_id="publication-decision-1",
        governed_subject_reference=result.governed_subject_reference,
        certification_result=result,
        requested_status="PUBLISH",
        decision_reasons=("Certified governed rule is eligible for publication review.",),
        limitations=result.limitations,
        evidence_trace_references=("evidence-trace-1",),
        decision_authority="governance:publication-review-v1",
    )
    values.update(overrides)
    return build_publication_decision_input(**values)


def test_contract_preserves_explicit_governed_input():
    result = build_input()
    assert result.requested_status == "PUBLISH"
    assert result.certification_result.outcome == "PASS"
    assert result.evidence_trace_references == ("evidence-trace-1",)


@pytest.mark.parametrize("status", ["PUBLISH", "WITHHOLD", "BLOCKED"])
def test_contract_supports_exact_publication_statuses(status):
    assert build_input(requested_status=status).requested_status == status


def test_contract_rejects_unknown_status_and_empty_reasons():
    with pytest.raises(PublicationDecisionContractError, match="requested_status"):
        build_input(requested_status="APPROVED")
    with pytest.raises(PublicationDecisionContractError, match="decision_reasons"):
        build_input(decision_reasons=())


def test_contract_rejects_subject_mismatch():
    with pytest.raises(PublicationDecisionContractError, match="must match"):
        build_input(governed_subject_reference="product:other")


def test_contract_rejects_duplicate_trace_and_invalid_version():
    with pytest.raises(PublicationDecisionContractError, match="unique"):
        build_input(evidence_trace_references=("trace", "trace"))
    with pytest.raises(PublicationDecisionContractError, match="contract_version"):
        build_publication_decision_input(
            decision_id="decision",
            governed_subject_reference=certification().governed_subject_reference,
            certification_result=certification(),
            requested_status="WITHHOLD",
            decision_reasons=("reason",),
            limitations=certification().limitations,
            evidence_trace_references=("trace",),
            decision_authority="authority",
            contract_version="2.0",
        )


def test_contract_is_frozen():
    result = build_input()
    with pytest.raises(FrozenInstanceError):
        result.decision_id = "changed"  # type: ignore[misc]


def test_contract_accepts_non_star_subject_without_code_change():
    result = replace(
        certification(),
        governed_subject_reference="governed-subject:motor:example-rule",
    )
    decision_input = build_input(
        governed_subject_reference=result.governed_subject_reference,
        certification_result=result,
    )
    assert decision_input.governed_subject_reference == "governed-subject:motor:example-rule"
