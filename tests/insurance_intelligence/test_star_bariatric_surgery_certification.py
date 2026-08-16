from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from insurance_intelligence.rule_certification.runner import run_rule_certification
from insurance_intelligence.rule_certification.star_health_bariatric_surgery import (
    STAR_COMPREHENSIVE_BARIATRIC_CANDIDATE_ID,
    STAR_COMPREHENSIVE_BARIATRIC_EVIDENCE_HASH,
    STAR_COMPREHENSIVE_BARIATRIC_SOURCE_EXCERPT,
    STAR_COMPREHENSIVE_POLICY_WORDING_SHA256,
    STAR_COMPREHENSIVE_SOURCE_REGISTRATION_SHA256,
    build_star_comprehensive_bariatric_surgery_case,
)


def _run(case):
    return run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
    )


def _mutate_requirement(case, component_id: str, **changes):
    requirement_id = f"requirement:star-comprehensive-bariatric:{component_id}"
    mutated = tuple(
        replace(result, **changes) if result.requirement_id == requirement_id else result
        for result in case.evidence_output.requirement_results
    )
    return replace(
        case,
        evidence_output=replace(case.evidence_output, requirement_results=mutated),
    )


def test_bariatric_case_uses_materially_different_generic_topic():
    case = build_star_comprehensive_bariatric_surgery_case()

    assert case.expectation.topic_id == "eligibility_and_consequence"
    assert case.expectation.topic_version == "1.0"
    assert case.domain == "health"
    assert case.expected_outcome == "PASS"
    assert {item.component_id for item in case.expectation.component_expectations} == {
        "eligibility_criteria",
        "applicability_scope",
        "eligible_consequence",
        "ineligible_consequence",
        "exception_condition",
    }


def test_bariatric_case_is_bound_to_authoritative_page_15_evidence():
    case = build_star_comprehensive_bariatric_surgery_case()

    assert len(case.evidence_output.evidence_packages) == 5
    for package in case.evidence_output.evidence_packages:
        assert package.subject_reference == "product:star_health:star_comprehensive"
        assert package.page == 15
        assert package.section == "II.15 Bariatric Surgery"
        assert package.source_type == "POLICY_WORDING"
        assert package.authority_requirement == "AUTHORITATIVE"
        assert package.source_excerpt == STAR_COMPREHENSIVE_BARIATRIC_SOURCE_EXCERPT
        assert package.lineage.source_artifact_sha256 == STAR_COMPREHENSIVE_POLICY_WORDING_SHA256
        assert package.lineage.governed_record_sha256 == STAR_COMPREHENSIVE_SOURCE_REGISTRATION_SHA256
        assert package.lineage.binding_reference.endswith(STAR_COMPREHENSIVE_BARIATRIC_CANDIDATE_ID)


def test_bariatric_semantics_keep_criteria_scope_and_consequences_separate():
    case = build_star_comprehensive_bariatric_surgery_case()
    claims = {
        package.field_or_topic: package.claim
        for package in case.evidence_output.evidence_packages
    }

    assert "BMI" in claims["ELIGIBILITY_CRITERIA"]
    assert "failed traditional weight-loss" in claims["ELIGIBILITY_CRITERIA"]
    assert "hospitalization for bariatric surgery" in claims["APPLICABILITY_SCOPE"]
    assert "payable" in claims["ELIGIBLE_CONSEQUENCE"]
    assert "does not apply" in claims["INELIGIBLE_CONSEQUENCE"]
    assert "cosmetic reasons" in claims["EXCEPTION_CONDITION"]
    assert "drug or alcohol abuse" in claims["EXCEPTION_CONDITION"]


def test_bariatric_case_passes_through_generic_runner():
    case = build_star_comprehensive_bariatric_surgery_case()
    result = _run(case)

    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert result.failures == ()
    assert {check.component_id: check.actual_status for check in result.component_checks} == {
        "eligibility_criteria": "SATISFIED",
        "applicability_scope": "SATISFIED",
        "eligible_consequence": "SATISFIED",
        "ineligible_consequence": "SATISFIED",
        "exception_condition": "SATISFIED",
    }


@pytest.mark.parametrize(
    "component_id",
    (
        "eligibility_criteria",
        "applicability_scope",
        "eligible_consequence",
        "ineligible_consequence",
    ),
)
def test_missing_required_semantics_block_certification(component_id: str):
    case = build_star_comprehensive_bariatric_surgery_case()
    mutated = _mutate_requirement(
        case,
        component_id,
        status="MISSING",
        matched_evidence_ids=(),
        missing_reason="required semantic removed by mutation",
        authority_satisfied=False,
        version_satisfied=False,
        lineage_satisfied=False,
        confidence=0.0,
    )

    result = _run(mutated)

    assert result.outcome != "PASS"
    assert result.actual_explanation_permitted is False
    assert component_id in {
        check.component_id for check in result.component_checks if check.actual_status == "MISSING"
    }


def test_conflicting_eligibility_semantics_block_certification():
    case = build_star_comprehensive_bariatric_surgery_case()
    mutated = _mutate_requirement(
        case,
        "eligibility_criteria",
        status="CONFLICTING",
        conflict_status="MATERIAL_CONFLICT",
        confidence=0.0,
    )

    result = _run(mutated)

    assert result.outcome != "PASS"
    assert result.actual_completeness_status == "CONFLICTING"
    assert result.actual_explanation_permitted is False


def test_bariatric_case_preserves_medical_and_claim_payment_boundaries():
    result = _run(build_star_comprehensive_bariatric_surgery_case())
    joined = " ".join(result.limitations).lower()

    assert "does not itself publish" in joined
    assert "does not decide individual medical suitability" in joined
    assert "does not guarantee claim admissibility or payment" in joined
    assert "claim will be paid" not in joined


def test_bariatric_case_is_deterministic_and_immutable():
    first = build_star_comprehensive_bariatric_surgery_case()
    second = build_star_comprehensive_bariatric_surgery_case()

    assert first == second
    with pytest.raises(FrozenInstanceError):
        first.case_id = "changed"  # type: ignore[misc]
