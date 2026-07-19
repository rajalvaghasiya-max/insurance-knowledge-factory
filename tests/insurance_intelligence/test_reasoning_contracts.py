from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from insurance_intelligence.contracts.evidence import EvidenceResolverOutput
from insurance_intelligence.contracts.reasoning import (
    ReasoningContractError,
    build_assumption,
    build_finding,
    build_input,
    build_output,
    build_requirement_result,
    build_rule_execution,
    build_trace_event,
    validate_output,
)
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


def make_evidence_output(request_id="req-1"):
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


def make_requirement_result(**overrides):
    values = dict(
        requirement_id="req_copay",
        status="SATISFIED",
        executed_rule_ids=("conditional_copayment_obligation_v1",),
        finding_ids=("finding-1",),
        rejected_rule_ids=(),
        missing_inputs=(),
        unsupported_reason=None,
        evidence_satisfied=True,
        context_satisfied=True,
        conflict_status="NONE",
        confidence=0.9,
    )
    values.update(overrides)
    return build_requirement_result(**values)


def make_finding(**overrides):
    values = dict(
        finding_id="finding-1",
        requirement_id="req_copay",
        finding_type="CLAIM_COST_SHARING",
        subject="insured",
        predicate="must_bear",
        object_or_effect="the documented percentage of the admissible claim amount",
        condition="the documented conditional co-payment trigger applies",
        scope="star_health:star_comprehensive",
        finding_status="CONDITIONAL",
        derivation_type="CONDITIONAL_DERIVATION",
        rule_id="conditional_copayment_obligation_v1",
        rule_version="1.0",
        evidence_ids=("evidence-1",),
        confidence=0.9,
    )
    values.update(overrides)
    return build_finding(**values)


def test_input_preserves_validated_cross_stage_contracts():
    result = build_input(
        request_id="req-1",
        reasoning_plan=make_plan(),
        evidence_resolution=make_evidence_output(),
        reasoning_context={"trigger_status": "UNKNOWN"},
    )
    assert result.request_id == "req-1"
    assert result.strict_mode == "STRICT"
    assert result.reasoning_context == {"trigger_status": "UNKNOWN"}


def test_input_rejects_request_id_mismatch_with_plan():
    with pytest.raises(ReasoningContractError, match="reasoning_plan"):
        build_input(request_id="req-2", reasoning_plan=make_plan(), evidence_resolution=make_evidence_output("req-2"))


def test_input_rejects_request_id_mismatch_with_evidence():
    with pytest.raises(ReasoningContractError, match="evidence_resolution"):
        build_input(request_id="req-1", reasoning_plan=make_plan(), evidence_resolution=make_evidence_output("req-2"))


def test_input_rejects_unknown_strict_mode():
    with pytest.raises(ReasoningContractError, match="strict_mode"):
        build_input(request_id="req-1", reasoning_plan=make_plan(), evidence_resolution=make_evidence_output(), strict_mode="LOOSE")


def test_input_is_frozen():
    result = build_input(request_id="req-1", reasoning_plan=make_plan(), evidence_resolution=make_evidence_output())
    with pytest.raises(FrozenInstanceError):
        result.request_id = "changed"  # type: ignore[misc]


def test_supported_finding_requires_evidence():
    with pytest.raises(ReasoningContractError, match="evidence_id"):
        make_finding(evidence_ids=())


def test_blocked_finding_may_have_no_evidence():
    finding = make_finding(finding_status="BLOCKED", evidence_ids=())
    assert finding.evidence_ids == ()


def test_finding_confidence_must_be_bounded():
    with pytest.raises(ReasoningContractError, match="between 0 and 1"):
        make_finding(confidence=1.1)


def test_finding_values_are_governed():
    with pytest.raises(ReasoningContractError, match="finding_type"):
        make_finding(finding_type="RECOMMENDATION")
    with pytest.raises(ReasoningContractError, match="derivation_type"):
        make_finding(derivation_type="FREE_FORM")


def test_assumption_values_are_governed_and_frozen():
    assumption = build_assumption(
        assumption_id="assumption-1",
        description="Trigger status supplied by caller",
        source="reasoning_context.trigger_status",
        approval_status="APPROVED_INPUT",
        used_by_finding_ids=("finding-1",),
        materiality="HIGH",
    )
    assert assumption.approval_status == "APPROVED_INPUT"
    with pytest.raises(FrozenInstanceError):
        assumption.source = "changed"  # type: ignore[misc]


def test_unapproved_assumption_cannot_be_used_by_finding():
    assumption = build_assumption(
        assumption_id="assumption-1",
        description="Unverified trigger status",
        source="unknown",
        approval_status="UNAPPROVED",
        used_by_finding_ids=("finding-1",),
    )
    with pytest.raises(ReasoningContractError, match="cannot be used"):
        build_output(
            request_id="req-1",
            reasoning_id="reasoning-1",
            findings=(make_finding(assumption_ids=("assumption-1",)),),
            requirement_results=(make_requirement_result(),),
            assumptions=(assumption,),
            reasoning_sufficiency="COMPLETE",
            reasoning_status="REASONED",
            confidence=0.9,
        )


def test_requirement_result_values_are_governed():
    with pytest.raises(ReasoningContractError, match="status"):
        make_requirement_result(status="DONE")


def test_rule_execution_values_are_governed():
    with pytest.raises(ReasoningContractError, match="status"):
        build_rule_execution(
            execution_id="exec-1",
            requirement_id="req_copay",
            rule_id="rule-1",
            rule_version="1.0",
            status="RUNNING",
        )


def test_trace_requires_positive_ordered_sequence():
    with pytest.raises(ReasoningContractError, match="positive integer"):
        build_trace_event(
            trace_id="trace-1",
            sequence=0,
            event_type="REASONING_STARTED",
            decision="START",
            basis="validated input",
            order_marker="0000",
        )


def test_output_accepts_consistent_graph():
    finding = make_finding()
    result = make_requirement_result()
    execution = build_rule_execution(
        execution_id="exec-1",
        requirement_id="req_copay",
        rule_id="conditional_copayment_obligation_v1",
        rule_version="1.0",
        status="EXECUTED",
        evidence_ids=("evidence-1",),
        output_finding_ids=("finding-1",),
        confidence=0.9,
    )
    trace = build_trace_event(
        trace_id="trace-1",
        sequence=1,
        event_type="FINDING_CREATED",
        requirement_id="req_copay",
        rule_id="conditional_copayment_obligation_v1",
        evidence_ids=("evidence-1",),
        decision="CREATED",
        basis="deterministic rule execution",
        output_finding_ids=("finding-1",),
        order_marker="0001",
    )
    output = build_output(
        request_id="req-1",
        reasoning_id="reasoning-1",
        findings=(finding,),
        requirement_results=(result,),
        rule_executions=(execution,),
        reasoning_sufficiency="COMPLETE",
        reasoning_status="REASONED",
        confidence=0.9,
        reasoning_trace=(trace,),
    )
    assert output.findings == (finding,)
    assert output.reasoning_status == "REASONED"


def test_output_rejects_duplicate_finding_ids():
    with pytest.raises(ReasoningContractError, match="finding_id"):
        build_output(
            request_id="req-1",
            reasoning_id="reasoning-1",
            findings=(make_finding(), make_finding()),
            requirement_results=(make_requirement_result(),),
            reasoning_sufficiency="COMPLETE",
            reasoning_status="REASONED",
            confidence=0.9,
        )


def test_output_rejects_finding_with_unknown_requirement():
    with pytest.raises(ReasoningContractError, match="unknown requirement"):
        build_output(
            request_id="req-1",
            reasoning_id="reasoning-1",
            findings=(make_finding(requirement_id="unknown"),),
            requirement_results=(make_requirement_result(),),
            reasoning_sufficiency="PARTIAL",
            reasoning_status="PARTIALLY_REASONED",
            confidence=0.5,
        )


def test_output_rejects_unknown_finding_reference_from_requirement_result():
    with pytest.raises(ReasoningContractError, match="unknown finding"):
        build_output(
            request_id="req-1",
            reasoning_id="reasoning-1",
            findings=(),
            requirement_results=(make_requirement_result(),),
            reasoning_sufficiency="BLOCKED",
            reasoning_status="NOT_REASONED",
            confidence=0.0,
        )


def test_output_rejects_unknown_assumption_reference():
    with pytest.raises(ReasoningContractError, match="unknown assumption"):
        build_output(
            request_id="req-1",
            reasoning_id="reasoning-1",
            findings=(make_finding(assumption_ids=("missing",)),),
            requirement_results=(make_requirement_result(),),
            reasoning_sufficiency="PARTIAL",
            reasoning_status="PARTIALLY_REASONED",
            confidence=0.5,
        )


def test_output_rejects_self_supporting_finding():
    with pytest.raises(ReasoningContractError, match="support itself"):
        build_output(
            request_id="req-1",
            reasoning_id="reasoning-1",
            findings=(make_finding(supporting_fact_ids=("finding-1",)),),
            requirement_results=(make_requirement_result(),),
            reasoning_sufficiency="COMPLETE",
            reasoning_status="REASONED",
            confidence=0.9,
        )


def test_output_rejects_out_of_order_trace():
    trace_2 = build_trace_event(
        trace_id="trace-2",
        sequence=2,
        event_type="REASONING_STARTED",
        decision="START",
        basis="validated input",
        order_marker="0002",
    )
    trace_1 = replace(trace_2, trace_id="trace-1", sequence=1, order_marker="0001")
    with pytest.raises(ReasoningContractError, match="unique and ordered"):
        build_output(
            request_id="req-1",
            reasoning_id="reasoning-1",
            reasoning_sufficiency="BLOCKED",
            reasoning_status="NOT_REASONED",
            confidence=0.0,
            reasoning_trace=(trace_2, trace_1),
        )


def test_output_status_and_sufficiency_are_governed():
    with pytest.raises(ReasoningContractError, match="reasoning_sufficiency"):
        build_output(
            request_id="req-1",
            reasoning_id="reasoning-1",
            reasoning_sufficiency="UNKNOWN",
            reasoning_status="NOT_REASONED",
            confidence=0.0,
        )


def test_output_contains_no_final_answer_field():
    output = build_output(
        request_id="req-1",
        reasoning_id="reasoning-1",
        reasoning_sufficiency="BLOCKED",
        reasoning_status="NOT_REASONED",
        confidence=0.0,
    )
    assert not hasattr(output, "answer")
    assert not hasattr(output, "recommendation")
    assert not hasattr(output, "explanation")
