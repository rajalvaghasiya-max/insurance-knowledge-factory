from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from insurance_intelligence.contracts.decision import build_input as build_decision_input
from insurance_intelligence.contracts.evidence import build_input as build_evidence_input
from insurance_intelligence.contracts.reasoning import build_input as build_reasoning_input
from insurance_intelligence.contracts.reasoning_plan import build_evidence_requirement, build_plan
from insurance_intelligence.decision.gate import DecisionSafetyGate, DecisionSafetyGateError
from insurance_intelligence.evidence.resolver import EvidenceResolver
from insurance_intelligence.reasoning.engine import ReasoningEngine

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "knowledge/factory/registry_backed"


def make_plan(*, status="READY", mode="INTERPRETIVE", outcome="CLAUSE_IMPACT_EXPLANATION"):
    evidence = () if status == "OUT_OF_SCOPE" else (
        build_evidence_requirement(
            requirement_id="req_copay",
            evidence_category="NORMALIZED_PRODUCT_FACT",
            subject_reference="star_health:star_comprehensive",
            required=True,
            authority_requirement="BINDING",
            version_requirement="ANY_GOVERNED",
            reason="reason over conditional co-payment",
            requested_by_step="step_1",
        ),
    )
    return build_plan(
        request_id="req-1", plan_id="plan-1", plan_type="CLAUSE_IMPACT_PLAN",
        execution_mode="NO_EXECUTION" if status == "OUT_OF_SCOPE" else mode,
        goal="derive conditional co-payment meaning", expected_outcome=outcome,
        plan_status=status, confidence=0.9, required_evidence=evidence,
    )


def pipeline(*, plan=None, reasoning_context=None):
    plan = plan or make_plan()
    evidence = EvidenceResolver().resolve(build_evidence_input(
        request_id="req-1", reasoning_plan=plan, repository_roots=(str(REGISTRY),), strict_mode="STRICT",
    ))
    reasoning = ReasoningEngine().reason(build_reasoning_input(
        request_id="req-1", reasoning_plan=plan, evidence_resolution=evidence,
        reasoning_context=reasoning_context or {}, strict_mode="STRICT",
    ))
    return plan, evidence, reasoning


def decide(*, plan=None, evidence=None, reasoning=None, context=None):
    if plan is None or evidence is None or reasoning is None:
        plan, evidence, reasoning = pipeline(plan=plan, reasoning_context=context)
    return DecisionSafetyGate().decide(build_decision_input(
        request_id="req-1", reasoning_plan=plan, evidence_resolution=evidence,
        reasoning_output=reasoning, decision_context=context or {}, strict_mode="STRICT",
    ))


def test_star_general_copay_meaning_is_approved_with_limitations():
    output = decide()
    assert output.decision == "APPROVED_WITH_LIMITATIONS"
    assert output.response_packet is not None
    assert output.response_packet.approved_finding_ids
    assert output.response_packet.approved_evidence_ids


def test_case_specific_missing_trigger_requires_clarification():
    output = decide(context={"case_specific_applicability": True})
    assert output.decision == "CLARIFICATION_REQUIRED"
    assert output.response_packet is None
    assert output.clarifications[0].required_context_keys == ("trigger_status",)


def test_case_specific_confirmed_trigger_is_approved():
    context = {"case_specific_applicability": True, "trigger_status": "CONFIRMED"}
    output = decide(context=context)
    assert output.decision in {"APPROVED", "APPROVED_WITH_LIMITATIONS"}
    assert output.response_packet is not None


def test_nontriggered_reasoning_is_approved():
    reasoning_context = {"case_specific_applicability": True, "conditional_copayment_trigger_status": "NOT_TRIGGERED"}
    plan, evidence, reasoning = pipeline(reasoning_context=reasoning_context)
    output = decide(plan=plan, evidence=evidence, reasoning=reasoning, context={"case_specific_applicability": True, "trigger_status": "NOT_TRIGGERED"})
    assert output.decision in {"APPROVED", "APPROVED_WITH_LIMITATIONS"}


def test_failed_lineage_is_insufficient_evidence():
    plan, evidence, reasoning = pipeline()
    package = evidence.evidence_packages[0]
    bad_lineage = replace(package.lineage, lineage_status="MISMATCH")
    bad_package = replace(package, lineage=bad_lineage)
    evidence = replace(evidence, evidence_packages=(bad_package,), sufficiency="FAILED_LINEAGE", resolution_status="NOT_RESOLVED")
    output = decide(plan=plan, evidence=evidence, reasoning=reasoning)
    assert output.decision == "INSUFFICIENT_EVIDENCE"
    assert output.response_packet is None


def test_version_unresolved_is_insufficient_evidence():
    plan, evidence, reasoning = pipeline()
    package = replace(evidence.evidence_packages[0], version_status="VERSION_UNRESOLVED")
    evidence = replace(evidence, evidence_packages=(package,), sufficiency="VERSION_UNRESOLVED", resolution_status="NOT_RESOLVED")
    assert decide(plan=plan, evidence=evidence, reasoning=reasoning).decision == "INSUFFICIENT_EVIDENCE"


def test_unsupported_recommendation_is_blocked():
    plan, evidence, reasoning = pipeline()
    output = decide(plan=plan, evidence=evidence, reasoning=reasoning, context={"requested_operations": ("RECOMMEND_PRODUCT",)})
    assert output.decision == "BLOCKED"
    assert output.response_packet is None


def test_out_of_scope_is_preserved():
    plan, evidence, reasoning = pipeline(plan=make_plan(status="OUT_OF_SCOPE"))
    output = decide(plan=plan, evidence=evidence, reasoning=reasoning)
    assert output.decision == "OUT_OF_SCOPE"


def test_response_packet_references_known_findings_and_evidence():
    plan, evidence, reasoning = pipeline()
    output = decide(plan=plan, evidence=evidence, reasoning=reasoning)
    packet = output.response_packet
    assert packet is not None
    assert set(packet.approved_finding_ids) <= {item.finding_id for item in reasoning.findings}
    assert set(packet.approved_evidence_ids) <= {item.evidence_id for item in evidence.evidence_packages}


def test_nonapproved_decision_does_not_leak_approved_findings():
    output = decide(context={"case_specific_applicability": True})
    assert output.response_packet is None


def test_trace_is_ordered_and_complete():
    output = decide()
    assert output.decision_trace[0].event_type == "DECISION_STARTED"
    assert output.decision_trace[-1].event_type == "DECISION_COMPLETED"
    assert [item.sequence for item in output.decision_trace] == list(range(1, len(output.decision_trace) + 1))
    assert any(item.event_type == "FINDING_APPROVED" for item in output.decision_trace)
    assert any(item.event_type == "RESPONSE_PACKET_ASSEMBLED" for item in output.decision_trace)


def test_clarification_trace_is_structured():
    output = decide(context={"case_specific_applicability": True})
    assert any(item.event_type == "CLARIFICATION_REQUIRED" for item in output.decision_trace)
    assert any(item.event_type == "FINDING_WITHHELD" for item in output.decision_trace)


def test_deterministic_output():
    assert decide() == decide()


def test_decision_id_changes_with_context():
    assert decide().decision_id != decide(context={"case_specific_applicability": True}).decision_id


def test_input_objects_are_not_mutated():
    plan, evidence, reasoning = pipeline()
    before = (repr(plan), repr(evidence), repr(reasoning))
    decide(plan=plan, evidence=evidence, reasoning=reasoning)
    assert before == (repr(plan), repr(evidence), repr(reasoning))


def test_gate_rejects_unvalidated_input():
    with pytest.raises(DecisionSafetyGateError):
        DecisionSafetyGate().decide(object())


def test_contract_rejects_cross_stage_request_mismatch():
    plan, evidence, reasoning = pipeline()
    with pytest.raises(Exception):
        build_decision_input(request_id="req-1", reasoning_plan=plan, evidence_resolution=replace(evidence, request_id="other"), reasoning_output=reasoning)


def test_no_final_answer_or_recommendation_fields():
    output = decide()
    assert not hasattr(output, "final_answer")
    assert not hasattr(output, "explanation")
    assert not hasattr(output, "recommendation")


def test_approved_packet_preserves_prohibited_operations():
    output = decide(context={"requested_operations": ("COMPARE_OPTIONS",)})
    assert output.response_packet is not None
    assert output.response_packet.prohibited_operations == ("COMPARE_OPTIONS",)


def test_unknown_requested_operations_are_preserved_not_executed():
    output = decide(context={"requested_operations": ("CUSTOM_OPERATION",)})
    assert output.response_packet is not None
    assert output.response_packet.prohibited_operations == ("CUSTOM_OPERATION",)
