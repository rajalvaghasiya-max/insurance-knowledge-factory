from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from insurance_intelligence.rule_certification.star_health import (
    STAR_COMPREHENSIVE_COPAYMENT_ASSERTION_ID,
    STAR_COMPREHENSIVE_COPAYMENT_BINDING_PATH,
    STAR_COMPREHENSIVE_COPAYMENT_EVIDENCE_HASH,
    STAR_COMPREHENSIVE_COPAYMENT_REVIEWED_STATEMENT,
    build_star_comprehensive_conditional_copayment_case,
    run_star_comprehensive_conditional_copayment_certification,
)


def test_exact_reviewed_statement_preserves_all_material_semantics():
    statement = STAR_COMPREHENSIVE_COPAYMENT_REVIEWED_STATEMENT

    assert "10% co-payment" in statement
    assert "each and every claim" in statement
    assert "age at entry is 61 years or above" in statement
    assert "does not apply" in statement
    assert "renewed continuously without a break" in statement
    assert "limits this co-payment to Sections" in statement
    assert "II.25" in statement


def test_case_is_bound_to_the_governed_star_artifact_and_primary_legal_evidence():
    case = build_star_comprehensive_conditional_copayment_case()

    assert case.expectation.governed_subject_reference == (
        "assertion:" + STAR_COMPREHENSIVE_COPAYMENT_ASSERTION_ID
    )
    assert case.expectation.topic_id == "conditional_obligation"
    assert case.expectation.topic_version == "1.0"
    assert case.domain == "health"

    assert len(case.evidence_output.evidence_packages) == 5
    for package in case.evidence_output.evidence_packages:
        assert package.subject_reference == "product:star_health:star_comprehensive"
        assert package.document_reference == "star_health_star_comprehensive_policy_wording_v1"
        assert package.page == 39
        assert package.source_type == "POLICY_WORDING"
        assert package.authority_requirement == "AUTHORITATIVE"
        assert package.source_excerpt == STAR_COMPREHENSIVE_COPAYMENT_REVIEWED_STATEMENT
        assert package.lineage.governed_record_path == STAR_COMPREHENSIVE_COPAYMENT_BINDING_PATH
        assert package.lineage.source_artifact_sha256 == STAR_COMPREHENSIVE_COPAYMENT_EVIDENCE_HASH
        assert package.lineage.binding_reference == (
            "assertion:" + STAR_COMPREHENSIVE_COPAYMENT_ASSERTION_ID
        )


def test_case_certifies_every_conditional_semantic_component_through_profiled_path():
    result = run_star_comprehensive_conditional_copayment_certification()

    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert result.failures == ()
    assert {check.component_id: check.actual_status for check in result.component_checks} == {
        "obligation_value": "SATISFIED",
        "trigger_condition": "SATISFIED",
        "applicability_scope": "SATISFIED",
        "exception_condition": "SATISFIED",
        "calculation_basis": "SATISFIED",
    }


def test_missing_star_exception_blocks_completeness_explanation_and_certification():
    case = build_star_comprehensive_conditional_copayment_case()
    evidence_output = replace(
        case.evidence_output,
        evidence_packages=tuple(
            package
            for package in case.evidence_output.evidence_packages
            if package.field_or_topic != "EXCEPTION_CONDITION"
        ),
        requirement_results=tuple(
            requirement
            for requirement in case.evidence_output.requirement_results
            if not requirement.requirement_id.endswith(":exception_condition")
        ),
    )

    result = run_star_comprehensive_conditional_copayment_certification(
        evidence_output=evidence_output,
    )

    assert result.outcome == "BLOCKED"
    assert result.actual_completeness_status == "PARTIAL"
    assert result.actual_explanation_permitted is False
    checks = {check.component_id: check for check in result.component_checks}
    assert checks["exception_condition"].actual_status == "MISSING"
    assert any("exception_condition" in failure for failure in result.failures)


def test_case_preserves_publication_and_claim_payment_limitations():
    result = run_star_comprehensive_conditional_copayment_certification()

    joined = " ".join(result.limitations).lower()
    assert "bound_not_published" in joined
    assert "internal certification" in joined
    assert "does not guarantee claim payment" in joined
    assert "claim will be paid" not in joined
    assert "claim is guaranteed" not in joined


def test_component_claims_keep_trigger_exception_scope_and_effect_separate():
    case = build_star_comprehensive_conditional_copayment_case()
    claims = {
        package.field_or_topic: package.claim
        for package in case.evidence_output.evidence_packages
    }

    assert "61 years or above" in claims["TRIGGER_CONDITION"]
    assert "does not apply" not in claims["TRIGGER_CONDITION"].lower()
    assert "does not apply" in claims["EXCEPTION_CONDITION"].lower()
    assert "before age 61" in claims["EXCEPTION_CONDITION"].lower()
    assert "sections" in claims["APPLICABILITY_SCOPE"].lower()
    assert "10%" in claims["OBLIGATION_VALUE"]
    assert "each and every claim" in claims["CALCULATION_BASIS"].lower()


def test_case_build_is_deterministic_and_immutable():
    first = build_star_comprehensive_conditional_copayment_case()
    second = build_star_comprehensive_conditional_copayment_case()

    assert first == second
    assert first.expected_outcome == "PASS"
    with pytest.raises(FrozenInstanceError):
        first.case_id = "changed"  # type: ignore[misc]
