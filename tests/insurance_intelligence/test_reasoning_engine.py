from pathlib import Path
from dataclasses import replace

import pytest

from insurance_intelligence.contracts.evidence import build_input as build_evidence_input
from insurance_intelligence.contracts.reasoning import build_input as build_reasoning_input
from insurance_intelligence.contracts.reasoning_plan import build_evidence_requirement, build_plan
from insurance_intelligence.evidence.resolver import EvidenceResolver
from insurance_intelligence.reasoning.engine import ReasoningEngine, ReasoningEngineError

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "knowledge/factory/registry_backed"


def make_plan(*, status="READY", mode="INTERPRETIVE", outcome="CLAUSE_IMPACT_EXPLANATION", evidence=True):
    requirements = ()
    if evidence:
        requirements = (
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
        request_id="req-1",
        plan_id="plan-1",
        plan_type="CLAUSE_IMPACT_PLAN",
        execution_mode=mode,
        goal="derive conditional co-payment meaning",
        expected_outcome=outcome,
        plan_status=status,
        confidence=0.9,
        required_evidence=requirements,
    )


def resolve(plan):
    return EvidenceResolver().resolve(
        build_evidence_input(
            request_id="req-1",
            reasoning_plan=plan,
            repository_roots=(str(REGISTRY),),
            strict_mode="STRICT",
        )
    )


def reason(*, plan=None, evidence=None, context=None):
    plan = plan or make_plan()
    evidence = evidence or resolve(plan)
    return ReasoningEngine().reason(
        build_reasoning_input(
            request_id="req-1",
            reasoning_plan=plan,
            evidence_resolution=evidence,
            reasoning_context=context or {},
            strict_mode="STRICT",
        )
    )


def test_star_copay_pilot_creates_evidence_linked_finding():
    output = reason()
    assert output.reasoning_status == "CONDITIONAL"
    assert output.reasoning_sufficiency == "CONDITIONAL"
    finding = next(item for item in output.findings if item.finding_type == "CLAIM_COST_SHARING")
    assert finding.rule_id == "conditional_copayment_obligation_v1"
    assert finding.subject == "insured"
    assert finding.object_or_effect == "10% of the admissible claim amount"
    assert finding.condition
    assert finding.evidence_ids


def test_direct_fact_plan_uses_direct_fact_rule():
    plan = make_plan(outcome="DIRECT_FACT_RESPONSE")
    output = reason(plan=plan)
    assert output.reasoning_status == "REASONED"
    assert {item.rule_id for item in output.findings} == {"direct_documented_fact_v1"}
    assert output.findings[0].derivation_type == "DIRECT_FACT"


def test_specific_trigger_not_applied_without_context():
    output = reason(context={"case_specific_applicability": True})
    assert output.reasoning_status == "PARTIALLY_REASONED"
    finding = output.findings[0]
    assert finding.finding_type == "UNRESOLVED_IMPLICATION"
    assert "cannot be concluded" in finding.object_or_effect


def test_specific_nontriggered_context_produces_supported_finding():
    output = reason(context={
        "case_specific_applicability": True,
        "conditional_copayment_trigger_status": "NOT_TRIGGERED",
    })
    assert output.reasoning_status == "REASONED"
    assert output.findings[0].rule_id == "conditional_copayment_nontriggered_v1"
    assert output.findings[0].finding_status == "SUPPORTED"


def test_missing_evidence_blocks_reasoning():
    plan = make_plan()
    evidence = replace(resolve(plan), evidence_packages=(), resolution_status="NOT_RESOLVED", sufficiency="MISSING")
    output = reason(plan=plan, evidence=evidence)
    assert output.reasoning_status == "NOT_REASONED"
    assert output.requirement_results[0].status == "BLOCKED_BY_EVIDENCE"
    assert not output.findings


def test_failed_lineage_blocks_supported_findings():
    plan = make_plan()
    evidence = resolve(plan)
    result = replace(evidence.requirement_results[0], status="FAILED_LINEAGE", lineage_satisfied=False)
    evidence = replace(evidence, requirement_results=(result,), evidence_packages=(), resolution_status="NOT_RESOLVED", sufficiency="FAILED_LINEAGE")
    output = reason(plan=plan, evidence=evidence)
    assert output.reasoning_sufficiency == "BLOCKED"
    assert not output.findings


def test_version_unresolved_blocks_reasoning():
    plan = make_plan()
    evidence = resolve(plan)
    result = replace(evidence.requirement_results[0], status="VERSION_UNRESOLVED", version_satisfied=False)
    evidence = replace(evidence, requirement_results=(result,), evidence_packages=(), resolution_status="NOT_RESOLVED", sufficiency="VERSION_UNRESOLVED")
    assert reason(plan=plan, evidence=evidence).reasoning_status == "NOT_REASONED"


def test_material_conflict_is_preserved():
    plan = make_plan()
    evidence = resolve(plan)
    result = replace(evidence.requirement_results[0], status="CONFLICTING", conflict_status="UNRESOLVED")
    evidence = replace(evidence, requirement_results=(result,), resolution_status="CONFLICTING", sufficiency="CONFLICTING")
    output = reason(plan=plan, evidence=evidence)
    assert output.reasoning_status == "CONFLICTING"
    assert not output.findings


def test_unsupported_recommendation_has_no_applicable_rule():
    plan = make_plan(outcome="CONDITIONAL_RECOMMENDATION")
    output = reason(plan=plan, context={"requirement_types": {"req_copay": "RECOMMEND"}})
    assert output.reasoning_status == "NOT_REASONED"
    assert output.requirement_results[0].status == "NO_APPLICABLE_RULE"
    assert output.unsupported_requirements == ("req_copay",)


def test_no_reasoning_required_does_not_execute_rules():
    plan = make_plan(evidence=False)
    evidence = resolve(plan)
    output = reason(plan=plan, evidence=evidence)
    assert output.reasoning_status == "NO_REASONING_REQUIRED"
    assert not output.rule_executions


def test_out_of_scope_does_not_execute_rules():
    plan = make_plan(status="OUT_OF_SCOPE", mode="NO_EXECUTION", evidence=False)
    output = reason(plan=plan, evidence=resolve(plan))
    assert output.reasoning_status == "OUT_OF_SCOPE"
    assert not output.rule_executions


def test_no_rupee_calculation_or_recommendation_fields():
    output = reason()
    finding = output.findings[0]
    assert "₹" not in finding.object_or_effect
    assert not hasattr(output, "final_answer")
    assert not hasattr(output, "recommendation")


def test_every_finding_references_known_evidence():
    plan = make_plan()
    evidence = resolve(plan)
    output = reason(plan=plan, evidence=evidence)
    known = {item.evidence_id for item in evidence.evidence_packages}
    assert all(set(item.evidence_ids) <= known for item in output.findings)


def test_trace_is_structured_and_complete():
    output = reason()
    assert output.reasoning_trace[0].event_type == "REASONING_STARTED"
    assert output.reasoning_trace[-1].event_type == "REASONING_COMPLETED"
    assert [item.sequence for item in output.reasoning_trace] == list(range(1, len(output.reasoning_trace) + 1))
    assert any(item.event_type == "RULE_EXECUTED" for item in output.reasoning_trace)
    assert any(item.event_type == "FINDING_CREATED" for item in output.reasoning_trace)


def test_deterministic_output():
    assert reason() == reason()


def test_inputs_are_not_mutated():
    plan = make_plan()
    evidence = resolve(plan)
    before_plan = repr(plan)
    before_evidence = repr(evidence)
    reason(plan=plan, evidence=evidence)
    assert repr(plan) == before_plan
    assert repr(evidence) == before_evidence


def test_engine_rejects_unvalidated_input():
    with pytest.raises(ReasoningEngineError):
        ReasoningEngine().reason(object())


def test_cross_stage_request_mismatch_is_rejected_by_contract():
    plan = make_plan()
    evidence = replace(resolve(plan), request_id="other")
    with pytest.raises(Exception):
        build_reasoning_input(request_id="req-1", reasoning_plan=plan, evidence_resolution=evidence)


def test_rule_executions_link_findings_and_evidence():
    output = reason()
    execution = next(item for item in output.rule_executions if item.status == "EXECUTED")
    assert execution.evidence_ids
    assert execution.output_finding_ids
    assert set(execution.output_finding_ids) <= {item.finding_id for item in output.findings}


def test_reasoning_id_changes_with_approved_context():
    assert reason().reasoning_id != reason(context={"case_specific_applicability": True}).reasoning_id
