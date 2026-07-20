from dataclasses import FrozenInstanceError, fields, replace

import pytest

from insurance_intelligence.contracts.decision import (
    DecisionContractError,
    build_approved_response_packet,
    build_blocked_content,
    build_clarification_requirement,
    build_finding_disposition,
    build_input,
    build_output,
    build_safety_issue,
    build_trace_event,
    validate_output,
)
from insurance_intelligence.contracts.evidence import EvidenceResolverOutput
from insurance_intelligence.contracts.reasoning import build_finding, build_output as build_reasoning_output
from insurance_intelligence.contracts.reasoning_plan import build_evidence_requirement, build_plan


def make_plan(request_id="req-1"):
    requirement = build_evidence_requirement(
        requirement_id="req_copay",
        evidence_category="NORMALIZED_PRODUCT_FACT",
        subject_reference="star_health:star_comprehensive",
        required=True,
        authority_requirement="BINDING",
        version_requirement="ANY_GOVERNED",
        reason="derive conditional co-payment meaning",
        requested_by_step="step_1",
    )
    return build_plan(
        request_id=request_id,
        plan_id="plan-1",
        plan_type="CLAUSE_IMPACT_PLAN",
        execution_mode="INTERPRETIVE",
        goal="derive supported clause meaning",
        expected_outcome="CLAUSE_IMPACT_EXPLANATION",
        plan_status="READY",
        confidence=0.9,
        required_evidence=(requirement,),
    )


def make_evidence(request_id="req-1"):
    return EvidenceResolverOutput(
        contract_version="1.0",
        request_id=request_id,
        resolution_id="resolution-1",
        evidence_packages=(),
        requirement_results=(),
        entity_resolutions=(),
        document_resolutions=(),
        conflicts=(),
        missing_evidence=(),
        sufficiency="SUFFICIENT",
        limitations=(),
        resolution_trace=(),
        resolution_status="RESOLVED",
        confidence=0.9,
    )


def make_reasoning(request_id="req-1"):
    return build_reasoning_output(
        request_id=request_id,
        reasoning_id="reasoning-1",
        findings=(),
        requirement_results=(),
        reasoning_sufficiency="SUFFICIENT",
        reasoning_status="REASONED",
        confidence=0.9,
    )


def make_disposition(**overrides):
    values = dict(
        finding_id="finding-1",
        disposition="APPROVED",
        approved_evidence_ids=("evidence-1",),
        basis="supported finding may be communicated",
        confidence=0.9,
    )
    values.update(overrides)
    return build_finding_disposition(**values)


def make_issue(**overrides):
    values = dict(
        issue_id="issue-1",
        issue_type="MISSING_CONTEXT",
        severity="HIGH",
        status="BLOCKING",
        description="case-specific trigger context is absent",
        policy_id="missing_context_v1",
        finding_ids=("finding-1",),
        blocking=True,
    )
    values.update(overrides)
    return build_safety_issue(**values)


def make_clarification(**overrides):
    values = dict(
        clarification_id="clarification-1",
        topic="conditional_copayment_trigger",
        question_key="treatment_location",
        reason="trigger applicability cannot be established",
        priority="HIGH",
        required_context_keys=("treatment_location",),
        related_finding_ids=("finding-1",),
    )
    values.update(overrides)
    return build_clarification_requirement(**values)


def test_input_preserves_validated_cross_stage_contracts():
    result = build_input(
        request_id="req-1",
        reasoning_plan=make_plan(),
        evidence_resolution=make_evidence(),
        reasoning_output=make_reasoning(),
        decision_context={"audience": "consumer"},
    )
    assert result.request_id == "req-1"
    assert result.strict_mode == "STRICT"
    assert result.decision_context == {"audience": "consumer"}


@pytest.mark.parametrize("stage", ["plan", "evidence", "reasoning"])
def test_input_rejects_cross_stage_request_mismatch(stage):
    plan = make_plan("req-2" if stage == "plan" else "req-1")
    evidence = make_evidence("req-2" if stage == "evidence" else "req-1")
    reasoning = make_reasoning("req-2" if stage == "reasoning" else "req-1")
    with pytest.raises(DecisionContractError, match=stage if stage != "plan" else "reasoning_plan"):
        build_input(
            request_id="req-1",
            reasoning_plan=plan,
            evidence_resolution=evidence,
            reasoning_output=reasoning,
        )


def test_input_is_frozen_and_rejects_unknown_mode():
    result = build_input(
        request_id="req-1",
        reasoning_plan=make_plan(),
        evidence_resolution=make_evidence(),
        reasoning_output=make_reasoning(),
    )
    with pytest.raises(FrozenInstanceError):
        result.request_id = "changed"  # type: ignore[misc]
    with pytest.raises(DecisionContractError, match="strict_mode"):
        build_input(
            request_id="req-1",
            reasoning_plan=make_plan(),
            evidence_resolution=make_evidence(),
            reasoning_output=make_reasoning(),
            strict_mode="LOOSE",
        )


def test_approved_disposition_requires_evidence_and_governed_value():
    with pytest.raises(DecisionContractError, match="evidence IDs"):
        make_disposition(approved_evidence_ids=())
    with pytest.raises(DecisionContractError, match="disposition"):
        make_disposition(disposition="PUBLISH")


def test_withheld_disposition_may_have_no_approved_evidence():
    result = make_disposition(
        disposition="WITHHELD_INSUFFICIENT_CONTEXT",
        approved_evidence_ids=(),
        clarification_ids=("clarification-1",),
    )
    assert result.approved_evidence_ids == ()


def test_safety_issue_is_governed_and_blocking_issue_cannot_be_waived():
    with pytest.raises(DecisionContractError, match="issue_type"):
        make_issue(issue_type="UNKNOWN")
    with pytest.raises(DecisionContractError, match="cannot be marked"):
        make_issue(status="WAIVED")


def test_required_clarification_requires_context_key():
    with pytest.raises(DecisionContractError, match="context key"):
        make_clarification(required_context_keys=())


def test_response_packet_preserves_evidence_for_approved_findings():
    with pytest.raises(DecisionContractError, match="evidence IDs"):
        build_approved_response_packet(packet_id="packet-1", approved_finding_ids=("finding-1",))
    packet = build_approved_response_packet(
        packet_id="packet-1",
        approved_finding_ids=("finding-1",),
        approved_evidence_ids=("evidence-1",),
        prohibited_operations=("RECOMMEND",),
    )
    assert packet.prohibited_operations == ("RECOMMEND",)


def test_blocked_content_reason_is_governed():
    with pytest.raises(DecisionContractError, match="reason"):
        build_blocked_content(
            blocked_content_id="blocked-1",
            source_type="FINDING",
            source_id="finding-1",
            reason="BAD",
            policy_id="policy-1",
        )


def test_trace_requires_positive_sequence_and_governed_event():
    with pytest.raises(DecisionContractError, match="positive integer"):
        build_trace_event(
            trace_id="trace-1",
            sequence=0,
            event_type="DECISION_STARTED",
            decision="START",
            basis="validated inputs",
            order_marker="0000",
        )
    with pytest.raises(DecisionContractError, match="event_type"):
        build_trace_event(
            trace_id="trace-1",
            sequence=1,
            event_type="THOUGHT",
            decision="START",
            basis="validated inputs",
            order_marker="0001",
        )


def test_approved_output_requires_packet_and_no_blocking_issue():
    with pytest.raises(DecisionContractError, match="response packet"):
        build_output(
            request_id="req-1",
            decision_id="decision-1",
            decision="APPROVED",
            finding_dispositions=(make_disposition(),),
            confidence=0.9,
        )
    packet = build_approved_response_packet(
        packet_id="packet-1",
        approved_finding_ids=("finding-1",),
        approved_evidence_ids=("evidence-1",),
    )
    with pytest.raises(DecisionContractError, match="blocking safety"):
        build_output(
            request_id="req-1",
            decision_id="decision-1",
            decision="APPROVED",
            finding_dispositions=(make_disposition(safety_issue_ids=("issue-1",)),),
            safety_issues=(make_issue(),),
            response_packet=packet,
            confidence=0.9,
        )


def test_approved_packet_may_only_reference_approved_dispositions():
    packet = build_approved_response_packet(
        packet_id="packet-1",
        approved_finding_ids=("finding-1",),
        approved_evidence_ids=("evidence-1",),
    )
    with pytest.raises(DecisionContractError, match="was not approved"):
        build_output(
            request_id="req-1",
            decision_id="decision-1",
            decision="APPROVED",
            finding_dispositions=(
                make_disposition(disposition="WITHHELD_UNSUPPORTED", approved_evidence_ids=()),
            ),
            response_packet=packet,
            confidence=0.5,
        )


def test_nonapproved_output_cannot_expose_approved_findings():
    packet = build_approved_response_packet(
        packet_id="packet-1",
        approved_finding_ids=("finding-1",),
        approved_evidence_ids=("evidence-1",),
    )
    with pytest.raises(DecisionContractError, match="cannot expose"):
        build_output(
            request_id="req-1",
            decision_id="decision-1",
            decision="INSUFFICIENT_CONTEXT",
            finding_dispositions=(make_disposition(),),
            response_packet=packet,
            confidence=0.4,
        )


def test_clarification_decision_requires_required_clarification():
    with pytest.raises(DecisionContractError, match="required clarification"):
        build_output(
            request_id="req-1",
            decision_id="decision-1",
            decision="CLARIFICATION_REQUIRED",
            confidence=0.4,
        )
    result = build_output(
        request_id="req-1",
        decision_id="decision-1",
        decision="CLARIFICATION_REQUIRED",
        finding_dispositions=(
            make_disposition(
                disposition="WITHHELD_FOR_CLARIFICATION",
                approved_evidence_ids=(),
                clarification_ids=("clarification-1",),
            ),
        ),
        clarifications=(make_clarification(),),
        confidence=0.4,
    )
    assert result.decision == "CLARIFICATION_REQUIRED"


def test_human_review_and_blocked_decisions_require_supporting_records():
    with pytest.raises(DecisionContractError, match="review reason"):
        build_output(
            request_id="req-1",
            decision_id="decision-1",
            decision="HUMAN_REVIEW_REQUIRED",
            confidence=0.3,
        )
    with pytest.raises(DecisionContractError, match="blocking evidence"):
        build_output(
            request_id="req-1",
            decision_id="decision-1",
            decision="BLOCKED",
            confidence=0.1,
        )


def test_output_rejects_unknown_cross_references():
    with pytest.raises(DecisionContractError, match="unknown safety issue"):
        build_output(
            request_id="req-1",
            decision_id="decision-1",
            decision="INSUFFICIENT_CONTEXT",
            finding_dispositions=(
                make_disposition(
                    disposition="WITHHELD_INSUFFICIENT_CONTEXT",
                    approved_evidence_ids=(),
                    safety_issue_ids=("missing",),
                ),
            ),
            confidence=0.2,
        )


def test_output_rejects_duplicate_ids_and_unordered_trace():
    issue = make_issue(finding_ids=())
    with pytest.raises(DecisionContractError, match="safety issue IDs"):
        build_output(
            request_id="req-1",
            decision_id="decision-1",
            decision="BLOCKED",
            safety_issues=(issue, issue),
            confidence=0.1,
        )
    trace_1 = build_trace_event(
        trace_id="trace-1",
        sequence=2,
        event_type="DECISION_COMPLETED",
        decision="DONE",
        basis="complete",
        order_marker="0002",
    )
    trace_2 = build_trace_event(
        trace_id="trace-2",
        sequence=1,
        event_type="DECISION_STARTED",
        decision="START",
        basis="validated",
        order_marker="0001",
    )
    with pytest.raises(DecisionContractError, match="unique and ordered"):
        build_output(
            request_id="req-1",
            decision_id="decision-1",
            decision="OUT_OF_SCOPE",
            decision_trace=(trace_1, trace_2),
            confidence=0.0,
        )


def test_output_confidence_is_bounded_and_contract_is_frozen():
    with pytest.raises(DecisionContractError, match="between 0 and 1"):
        build_output(
            request_id="req-1",
            decision_id="decision-1",
            decision="OUT_OF_SCOPE",
            confidence=1.1,
        )
    result = build_output(
        request_id="req-1",
        decision_id="decision-1",
        decision="OUT_OF_SCOPE",
        confidence=0.0,
    )
    with pytest.raises(FrozenInstanceError):
        result.decision = "APPROVED"  # type: ignore[misc]


def test_contract_contains_no_final_answer_or_explanation_fields():
    names = {field.name for field in fields(type(build_output(
        request_id="req-1",
        decision_id="decision-1",
        decision="OUT_OF_SCOPE",
        confidence=0.0,
    )))}
    assert "answer" not in names
    assert "explanation" not in names
    assert "recommendation" not in names


def test_validate_output_rejects_wrong_type():
    with pytest.raises(DecisionContractError, match="DecisionGateOutput"):
        validate_output(object())  # type: ignore[arg-type]
