from __future__ import annotations

from dataclasses import replace

import pytest

from insurance_intelligence.contracts.publication_decision import (
    build_publication_decision_input,
)
from insurance_intelligence.publication_decision.evaluator import (
    PublicationDecisionEvaluationError,
    evaluate_publication_decision,
)
from insurance_intelligence.rule_certification.runner import run_rule_certification
from insurance_intelligence.rule_certification.star_health import (
    build_star_comprehensive_conditional_copayment_case,
)
from insurance_intelligence.rule_certification.star_health_room_rent import (
    build_star_comprehensive_room_rent_case,
)


def certification(*, copayment=False, outcome="PASS", trace=True):
    case = (
        build_star_comprehensive_conditional_copayment_case()
        if copayment
        else build_star_comprehensive_room_rent_case()
    )
    result = run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
        trace_references=("certification-trace-1",) if trace else (),
    )
    return replace(result, outcome=outcome)


def decide(*, result=None, status="PUBLISH", limitations=None, evidence_trace=("evidence-trace-1",)):
    result = result or certification()
    decision_input = build_publication_decision_input(
        decision_id="publication-decision-1",
        governed_subject_reference=result.governed_subject_reference,
        certification_result=result,
        requested_status=status,
        decision_reasons=("Apply deterministic publication governance.",),
        limitations=result.limitations if limitations is None else limitations,
        evidence_trace_references=evidence_trace,
        decision_authority="governance:publication-review-v1",
    )
    return evaluate_publication_decision(decision_input)


def test_pass_certification_can_publish_with_complete_trace():
    result = decide()
    assert result.decision_status == "PUBLISH"
    assert result.publication_permitted is True
    assert result.failures == ()


def test_pass_certification_can_be_explicitly_withheld():
    result = decide(status="WITHHOLD")
    assert result.decision_status == "WITHHOLD"
    assert result.publication_permitted is False


@pytest.mark.parametrize("outcome", ["FAIL", "BLOCKED"])
def test_nonpassing_certification_forces_blocked(outcome):
    result = decide(result=certification(outcome=outcome), status="PUBLISH")
    assert result.decision_status == "BLOCKED"
    assert result.publication_permitted is False
    assert outcome in result.failures[-1]


def test_explicit_blocked_remains_blocked():
    result = decide(status="BLOCKED")
    assert result.decision_status == "BLOCKED"
    assert result.publication_permitted is False


def test_publish_requires_certification_and_evidence_trace():
    missing_certification_trace = decide(result=certification(trace=False))
    assert missing_certification_trace.decision_status == "BLOCKED"
    assert "Certification trace references are required." in missing_certification_trace.failures

    missing_evidence_trace = decide(evidence_trace=())
    assert missing_evidence_trace.decision_status == "BLOCKED"
    assert "Evidence trace references are required." in missing_evidence_trace.failures


def test_all_certification_limitations_must_be_preserved():
    result = certification()
    decision = decide(result=result, limitations=result.limitations[:-1])
    assert decision.decision_status == "BLOCKED"
    assert "Certification limitations were not fully preserved." in decision.failures


def test_bound_not_published_cannot_be_treated_as_published():
    result = decide(result=certification(copayment=True), status="PUBLISH")
    assert result.decision_status == "BLOCKED"
    assert result.publication_permitted is False
    assert any("bound_not_published" in failure for failure in result.failures)


def test_file_presence_is_not_an_input_or_decision_signal(tmp_path):
    (tmp_path / "publication.json").write_text("{}", encoding="utf-8")
    first = decide()
    second = decide()
    assert first == second
    assert first.decision_status == "PUBLISH"


def test_output_is_deterministic_and_does_not_mutate_input():
    result = certification()
    before = repr(result)
    first = decide(result=result)
    second = decide(result=result)
    assert first == second
    assert repr(result) == before


def test_non_star_subject_uses_same_evaluator():
    generic = replace(
        certification(),
        governed_subject_reference="governed-subject:life:generic-rule",
    )
    result = decide(result=generic)
    assert result.decision_status == "PUBLISH"
    assert result.governed_subject_reference == "governed-subject:life:generic-rule"


def test_p2_3_never_creates_authoritative_publication():
    result = decide()
    assert result.authoritative_publication_created is False
    assert not hasattr(result, "final_answer")
    assert not hasattr(result, "explanation")
    assert not hasattr(result, "recommendation")
    assert not hasattr(result, "claim_payment")


def test_evaluator_rejects_unvalidated_input():
    with pytest.raises(PublicationDecisionEvaluationError):
        evaluate_publication_decision(object())  # type: ignore[arg-type]
