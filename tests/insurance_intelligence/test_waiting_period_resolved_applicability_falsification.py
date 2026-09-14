from dataclasses import replace

from insurance_intelligence.contracts.reasoning import build_input as build_reasoning_input
from insurance_intelligence.contracts.reasoning_plan import build_evidence_requirement, build_plan
from insurance_intelligence.reasoning.engine import ReasoningEngine
from insurance_intelligence.rule_certification.star_health_initial_waiting_period import (
    build_star_comprehensive_initial_waiting_period_case,
)


REQUIREMENT_ID = "requirement:waiting-period-resolved-applicability"


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
        reason="assess governed waiting-period applicability against approved case facts",
        requested_by_step="DERIVE_INSURANCE_IMPLICATIONS",
    )
    plan = build_plan(
        request_id=request_id,
        plan_id="plan:waiting-period-resolved-applicability",
        plan_type="CLAUSE_IMPACT_PLAN",
        execution_mode="INTERPRETIVE",
        goal="determine whether the governed waiting period is still active for the case",
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
        reasoning_context={
            "case_specific_applicability": True,
            "policy_start_date": "2026-01-01",
            "claim_date": "2026-01-15",
            "waiting_period_continuity_credit_status": "NOT_APPLICABLE",
            "waiting_period_exception_status": "NOT_APPLICABLE",
        },
        strict_mode="STRICT",
    )


def test_sufficient_approved_case_context_resolves_waiting_period_applicability() -> None:
    """Falsification: sufficient approved case facts must resolve the timeline state.

    The selected dates are safely inside a documented 30-day initial waiting period,
    so boundary-convention ambiguity cannot change the result. Explicit context also
    states that no continuity credit and no exception applies. The reasoning engine
    must therefore produce a supported resolved implication rather than the existing
    unresolved-context finding.
    """

    output = ReasoningEngine().reason(_reasoning_input())
    result = output.requirement_results[0]

    assert result.status == "SATISFIED"
    assert "waiting_period_applicability_unresolved_v1" not in result.executed_rule_ids
    assert output.findings
    assert all(item.finding_type != "UNRESOLVED_IMPLICATION" for item in output.findings)
    assert any(item.finding_status == "SUPPORTED" for item in output.findings)
    rendered = " ".join(item.object_or_effect.casefold() for item in output.findings)
    assert "waiting period" in rendered
    assert "not complete" in rendered or "still active" in rendered
