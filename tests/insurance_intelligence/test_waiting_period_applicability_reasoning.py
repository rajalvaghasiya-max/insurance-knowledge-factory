from dataclasses import replace
from pathlib import Path

from insurance_intelligence.contracts.reasoning import build_input as build_reasoning_input
from insurance_intelligence.contracts.reasoning_plan import build_evidence_requirement, build_plan
from insurance_intelligence.reasoning.engine import ReasoningEngine, _requirement_type, _topic
from insurance_intelligence.reasoning.rules import rule_definitions
from insurance_intelligence.rule_certification.star_health_initial_waiting_period import (
    build_star_comprehensive_initial_waiting_period_case,
)


REQUIREMENT_ID = "requirement:waiting-period-applicability"


def _reasoning_input():
    case = build_star_comprehensive_initial_waiting_period_case()
    request_id = case.evidence_output.request_id
    evidence_ids = tuple(item.evidence_id for item in case.evidence_output.evidence_packages)
    requirement = build_evidence_requirement(
        requirement_id=REQUIREMENT_ID,
        evidence_category="NORMALIZED_PRODUCT_FACT",
        subject_reference="product:governed-health-product",
        required=True,
        authority_requirement="AUTHORITATIVE",
        version_requirement="ANY_GOVERNED",
        reason="assess governed waiting-period applicability",
        requested_by_step="DERIVE_INSURANCE_IMPLICATIONS",
    )
    plan = build_plan(
        request_id=request_id,
        plan_id="plan:waiting-period-applicability",
        plan_type="CLAUSE_IMPACT_PLAN",
        execution_mode="INTERPRETIVE",
        goal="determine whether the governed waiting period applies in the case",
        expected_outcome="CLAUSE_IMPACT_EXPLANATION",
        plan_status="READY",
        confidence=1.0,
        required_evidence=(requirement,),
    )
    evidence = tuple(
        replace(item, requirement_id=REQUIREMENT_ID)
        for item in case.evidence_output.evidence_packages
    )
    unified_result = replace(
        case.evidence_output.requirement_results[0],
        requirement_id=REQUIREMENT_ID,
        matched_evidence_ids=evidence_ids,
    )
    evidence_output = replace(
        case.evidence_output,
        evidence_packages=evidence,
        requirement_results=(unified_result,),
    )
    return build_reasoning_input(
        request_id=request_id,
        reasoning_plan=plan,
        evidence_resolution=evidence_output,
        reasoning_context={"case_specific_applicability": True},
        strict_mode="STRICT",
    )


def test_waiting_period_applicability_uses_topic_specific_assess_applicability_rule() -> None:
    reasoning_input = _reasoning_input()

    assert _topic(reasoning_input.evidence_resolution.evidence_packages) == "waiting_period"
    assert _requirement_type(reasoning_input, REQUIREMENT_ID) == "ASSESS_APPLICABILITY"

    output = ReasoningEngine().reason(reasoning_input)
    result = output.requirement_results[0]

    assert result.status == "PARTIALLY_SATISFIED"
    assert result.executed_rule_ids == ("waiting_period_applicability_unresolved_v1",)
    assert len(output.findings) == 1
    finding = output.findings[0]
    assert finding.rule_id == "waiting_period_applicability_unresolved_v1"
    assert finding.finding_type == "UNRESOLVED_IMPLICATION"
    assert finding.finding_status == "PARTIALLY_SUPPORTED"
    assert "30 days" in (finding.condition or "")
    assert "first policy commencement date" in (finding.condition or "")
    assert finding.applicability_scope is not None
    assert "enhanced Sum Insured" in finding.applicability_scope
    assert finding.exception is not None
    assert "continuous coverage" in finding.exception
    assert "accident" in finding.exception
    assert set(finding.evidence_ids) == {
        item.evidence_id for item in reasoning_input.evidence_resolution.evidence_packages
    }


def test_waiting_period_rule_is_narrowly_registered() -> None:
    rule = next(
        item for item in rule_definitions()
        if item.rule_id == "waiting_period_applicability_unresolved_v1"
    )

    assert rule.topic == "waiting_period"
    assert rule.supported_requirement_types == ("ASSESS_APPLICABILITY",)
    assert rule.required_evidence_topics == ("waiting_period",)
    assert "DERIVE_IMPLICATIONS" not in rule.supported_requirement_types


def test_waiting_period_rule_contains_no_product_specific_runtime_identifier() -> None:
    source = Path("insurance_intelligence/reasoning/rules.py").read_text(encoding="utf-8").lower()

    assert "star_health" not in source
    assert "star comprehensive" not in source
    assert "bajaj" not in source
    assert "hdfc" not in source
