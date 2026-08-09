from dataclasses import replace
from pathlib import Path

from insurance_intelligence.contracts.evidence import build_input as build_evidence_input
from insurance_intelligence.contracts.reasoning import build_input as build_reasoning_input
from insurance_intelligence.contracts.reasoning_plan import build_evidence_requirement, build_plan
from insurance_intelligence.evidence.resolver import EvidenceResolver
from insurance_intelligence.reasoning import engine as engine_module
from insurance_intelligence.reasoning.engine import ReasoningEngine
from insurance_intelligence.reasoning.registry import ReasoningRuleRegistry
from insurance_intelligence.reasoning.rules import execute_rule as real_execute_rule, rule_definitions


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = ROOT / "knowledge/factory/registry_backed"


def _plan():
    requirement = build_evidence_requirement(
        requirement_id="req_copay",
        evidence_category="NORMALIZED_PRODUCT_FACT",
        subject_reference="star_health:star_comprehensive",
        required=True,
        authority_requirement="BINDING",
        version_requirement="ANY_GOVERNED",
        reason="reason over conditional co-payment",
        requested_by_step="step_1",
    )
    return build_plan(
        request_id="req-1",
        plan_id="plan-1",
        plan_type="CLAUSE_IMPACT_PLAN",
        execution_mode="INTERPRETIVE",
        goal="derive conditional co-payment meaning",
        expected_outcome="CLAUSE_IMPACT_EXPLANATION",
        plan_status="READY",
        confidence=0.9,
        required_evidence=(requirement,),
    )


def _input():
    plan = _plan()
    evidence = EvidenceResolver().resolve(
        build_evidence_input(
            request_id="req-1",
            reasoning_plan=plan,
            repository_roots=(str(REGISTRY_ROOT),),
            strict_mode="STRICT",
        )
    )
    return build_reasoning_input(
        request_id="req-1",
        reasoning_plan=plan,
        evidence_resolution=evidence,
        reasoning_context={},
        strict_mode="STRICT",
    )


def _copay_only_registry():
    definition = next(
        item
        for item in rule_definitions()
        if item.rule_id == "conditional_copayment_obligation_v1"
    )
    return ReasoningRuleRegistry((definition,))


def test_registered_runtime_finding_type_is_accepted():
    output = ReasoningEngine(_copay_only_registry()).reason(_input())

    assert len(output.findings) == 1
    assert output.findings[0].finding_type == "CLAIM_COST_SHARING"
    assert output.rule_executions[0].status == "EXECUTED"
    assert output.requirement_results[0].status == "CONDITIONAL"


def test_unregistered_runtime_finding_type_is_rejected_fail_closed(monkeypatch):
    def wrong_type_executor(rule_id, data):
        produced = real_execute_rule(rule_id, data)
        if rule_id == "conditional_copayment_obligation_v1":
            return tuple(replace(item, finding_type="DOCUMENTED_FACT") for item in produced)
        return produced

    monkeypatch.setattr(engine_module, "execute_rule", wrong_type_executor)

    output = ReasoningEngine(_copay_only_registry()).reason(_input())

    assert output.findings == ()
    assert output.rule_executions[0].status == "REJECTED"
    assert "unregistered finding types" in (output.rule_executions[0].rejection_reason or "")
    assert output.requirement_results[0].status == "UNSUPPORTED"
    assert output.requirement_results[0].finding_ids == ()
    assert output.reasoning_status == "NOT_REASONED"
    assert output.reasoning_sufficiency == "UNSUPPORTED"
