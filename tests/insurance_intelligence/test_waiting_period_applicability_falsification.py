from dataclasses import replace

from insurance_intelligence.contracts.reasoning import build_input as build_reasoning_input
from insurance_intelligence.contracts.reasoning_plan import build_evidence_requirement, build_plan
from insurance_intelligence.reasoning.engine import ReasoningEngine, _requirement_type
from insurance_intelligence.rule_certification.star_health_initial_waiting_period import (
    build_star_comprehensive_initial_waiting_period_case,
)


REQUIREMENT_ID = "requirement:star-comprehensive-waiting-period-applicability"


def _interpretive_waiting_period_inputs():
    case = build_star_comprehensive_initial_waiting_period_case()
    request_id = case.evidence_output.request_id
    evidence_ids = tuple(item.evidence_id for item in case.evidence_output.evidence_packages)

    requirement = build_evidence_requirement(
        requirement_id=REQUIREMENT_ID,
        evidence_category="NORMALIZED_PRODUCT_FACT",
        subject_reference="product:star_health:star_comprehensive",
        required=True,
        authority_requirement="AUTHORITATIVE",
        version_requirement="ANY_GOVERNED",
        reason="assess whether the governed initial waiting period applies in the described situation",
        requested_by_step="DERIVE_INSURANCE_IMPLICATIONS",
    )
    plan = build_plan(
        request_id=request_id,
        plan_id="plan:star-comprehensive-waiting-period-applicability",
        plan_type="CLAUSE_IMPACT_PLAN",
        execution_mode="INTERPRETIVE",
        goal="determine whether the initial waiting period applies in the described situation",
        expected_outcome="CLAUSE_IMPACT_EXPLANATION",
        plan_status="READY",
        confidence=1.0,
        required_evidence=(requirement,),
    )

    # Certification stores each semantic component under its own certification
    # requirement. Runtime reasoning consumes the same certified evidence as one
    # planner requirement, so the harness changes only requirement grouping.
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
    reasoning_input = build_reasoning_input(
        request_id=request_id,
        reasoning_plan=plan,
        evidence_resolution=evidence_output,
        reasoning_context={},
        strict_mode="STRICT",
    )
    return plan, evidence_output, reasoning_input


def test_interpretive_waiting_period_routes_to_applicability_requirement() -> None:
    _, _, reasoning_input = _interpretive_waiting_period_inputs()

    assert _requirement_type(reasoning_input, REQUIREMENT_ID) == "ASSESS_APPLICABILITY"


def test_waiting_period_has_no_substantive_reasoning_before_applicability_rule_exists() -> None:
    _, _, reasoning_input = _interpretive_waiting_period_inputs()

    output = ReasoningEngine().reason(reasoning_input)
    result = output.requirement_results[0]

    assert result.status == "NO_APPLICABLE_RULE"
    assert output.findings == ()
    assert output.rule_executions == ()
