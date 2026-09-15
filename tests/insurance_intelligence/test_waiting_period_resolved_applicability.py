from dataclasses import replace

from insurance_intelligence.contracts.reasoning import build_input as build_reasoning_input
from insurance_intelligence.contracts.reasoning_plan import build_evidence_requirement, build_plan
from insurance_intelligence.reasoning.engine import ReasoningEngine
from insurance_intelligence.rule_certification.star_health_initial_waiting_period import (
    build_star_comprehensive_initial_waiting_period_case,
)


REQUIREMENT_ID = "requirement:waiting-period-resolved-applicability"


def _reasoning_input(*, claim_date: str, context_overrides: dict | None = None):
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
    context = {
        "case_specific_applicability": True,
        "policy_start_date": "2026-01-01",
        "claim_date": claim_date,
        "waiting_period_continuity_credit_status": "NOT_APPLICABLE",
        "waiting_period_exception_status": "NOT_APPLICABLE",
    }
    if context_overrides:
        context.update(context_overrides)
    return build_reasoning_input(
        request_id=request_id,
        reasoning_plan=plan,
        evidence_resolution=evidence_output,
        reasoning_context=context,
        strict_mode="STRICT",
    )


def test_inside_period_resolves_as_still_active() -> None:
    output = ReasoningEngine().reason(_reasoning_input(claim_date="2026-01-15"))
    result = output.requirement_results[0]

    assert result.status == "SATISFIED"
    assert result.executed_rule_ids == ("waiting_period_applicability_resolved_v1",)
    assert len(output.findings) == 1
    finding = output.findings[0]
    assert finding.finding_status == "SUPPORTED"
    assert finding.finding_type == "CLAIM_CONDITION"
    assert finding.predicate == "is_still_active"
    assert "not complete" in finding.object_or_effect
    assert set(finding.evidence_ids) == {
        item.evidence_id for item in _reasoning_input(claim_date="2026-01-15").evidence_resolution.evidence_packages
    }


def test_after_period_resolves_as_complete() -> None:
    output = ReasoningEngine().reason(_reasoning_input(claim_date="2026-02-15"))
    finding = output.findings[0]

    assert output.requirement_results[0].status == "SATISFIED"
    assert finding.rule_id == "waiting_period_applicability_resolved_v1"
    assert finding.predicate == "is_complete"
    assert "is complete" in finding.object_or_effect


def test_exact_boundary_fails_closed_without_inventing_activation_convention() -> None:
    output = ReasoningEngine().reason(_reasoning_input(claim_date="2026-01-31"))
    result = output.requirement_results[0]

    assert result.status == "UNSUPPORTED"
    assert "waiting_period_applicability_resolved_v1" in result.rejected_rule_ids
    assert "waiting_period_applicability_unresolved_v1" in result.rejected_rule_ids
    assert not output.findings


def test_missing_material_case_fact_preserves_existing_unresolved_fallback() -> None:
    data = _reasoning_input(claim_date="2026-01-15")
    context = dict(data.reasoning_context)
    context.pop("waiting_period_exception_status")
    data = replace(data, reasoning_context=context)

    output = ReasoningEngine().reason(data)
    result = output.requirement_results[0]

    assert result.status == "PARTIALLY_SATISFIED"
    assert result.executed_rule_ids == ("waiting_period_applicability_unresolved_v1",)
    assert output.findings[0].finding_type == "UNRESOLVED_IMPLICATION"
