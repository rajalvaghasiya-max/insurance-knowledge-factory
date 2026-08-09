from dataclasses import replace

import pytest

from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentBand,
    AssessmentStatus,
    DecisionRole,
)
from insurance_intelligence.benefits.condition_assessment_projection import (
    ConditionAssessmentProjectionError,
    GovernedConditionAssessmentProjection,
    project_conditional_copayment_finding,
)
from insurance_intelligence.benefits.copayment_assessment import (
    assess_conditional_copayment,
)
from insurance_intelligence.benefits.copayment_assessment_policy import (
    COPAYMENT_ASSESSMENT_POLICY,
)
from insurance_intelligence.contracts.evidence import EvidencePackage, Lineage
from insurance_intelligence.reasoning.rules import (
    build_rule_input,
    conditional_copayment_obligation,
)


STAR_STATEMENT = (
    "Star Comprehensive applies a 10% co-payment to each and every claim for fresh as well as renewal policies "
    "where the insured person's age at entry is 61 years or above. The co-payment does not apply where the "
    "insured person entered the policy before attaining 61 years of age and renewed continuously without a "
    "break. The policy wording limits this co-payment to Sections II.1, II.2, II.3, II.4, II.5, II.6, II.7, "
    "II.8, II.9, II.10, II.11, II.15 and II.25."
)


def _evidence(claim: str = STAR_STATEMENT) -> EvidencePackage:
    return EvidencePackage(
        evidence_id="ev-star-copay-mo026c",
        requirement_id="req-star-copay-mo026c",
        subject_reference="Star Comprehensive",
        governed_entity_reference="star_health:star_comprehensive",
        field_or_topic="conditional_copayment",
        claim=claim,
        evidence_role="SUPPORTING",
        source_type="POLICY_WORDING",
        document_reference="star-policy-wording",
        document_version="v1",
        effective_from=None,
        effective_to=None,
        page=39,
        section="Conditional co-payment",
        source_excerpt=claim,
        normalized_fact_reference="canonical:conditional_copayment",
        authority_rank=1,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=Lineage(
            "source.pdf",
            "a" * 64,
            "binding.json",
            "b" * 64,
            "binding",
            "projection",
            "VERIFIED",
        ),
        retrieval_basis=("binding", "canonical_projection"),
        confidence=0.98,
    )


def _star_finding():
    data = build_rule_input(
        requirement_id="req-star-copay-mo026c",
        evidence=(_evidence(),),
        approved_context={},
    )
    return conditional_copayment_obligation(data)[0]


def test_copayment_policy_is_governed_and_versioned() -> None:
    assert COPAYMENT_ASSESSMENT_POLICY.is_governed_for_use is True
    assert COPAYMENT_ASSESSMENT_POLICY.policy_version == "1.0"
    assert "protection-floor" in COPAYMENT_ASSESSMENT_POLICY.governance_basis.lower()
    assert "product-level trade-offs" in COPAYMENT_ASSESSMENT_POLICY.governance_basis.lower()


def test_star_reasoning_finding_projects_without_duplicate_benefit_model() -> None:
    finding = _star_finding()
    projection = project_conditional_copayment_finding(finding)
    assert projection.dimension_id == "copayment"
    assert projection.finding_id == finding.finding_id
    assert projection.percentage == 10.0
    assert projection.evidence_ids == finding.evidence_ids
    assert projection.rule_id == finding.rule_id
    assert projection.rule_version == finding.rule_version


def test_star_projection_preserves_trigger_exception_and_scope() -> None:
    projection = project_conditional_copayment_finding(_star_finding())
    assert projection.trigger == "where the insured person's age at entry is 61 years or above"
    assert projection.exception == (
        "The co-payment does not apply where the insured person entered the policy before attaining 61 years "
        "of age and renewed continuously without a break"
    )
    assert projection.applicability_scope == (
        "The policy wording limits this co-payment to Sections II.1, II.2, II.3, II.4, II.5, II.6, II.7, "
        "II.8, II.9, II.10, II.11, II.15 and II.25"
    )


def test_star_copayment_is_restrictive_protection_floor() -> None:
    result = assess_conditional_copayment(
        project_conditional_copayment_finding(_star_finding())
    )
    assert result.status is AssessmentStatus.ASSESSED_WITH_LIMITATIONS
    assert result.assessment_band is AssessmentBand.RESTRICTIVE
    assert result.decision_role is DecisionRole.PROTECTION_FLOOR
    assert result.assessment_policy_version == "1.0"
    assert "10%" in result.summary
    assert "conditional" in result.summary.lower()


def test_star_assessment_preserves_evidence_lineage() -> None:
    finding = _star_finding()
    result = assess_conditional_copayment(project_conditional_copayment_finding(finding))
    assert result.evidence_reference_ids == finding.evidence_ids
    assert result.implementation_id == f"reasoning_finding:{finding.finding_id}"


def test_copayment_warning_cannot_be_lost_in_clean_status() -> None:
    result = assess_conditional_copayment(
        project_conditional_copayment_finding(_star_finding())
    )
    assert result.status is AssessmentStatus.ASSESSED_WITH_LIMITATIONS
    assert result.limitations
    assert "actual applicability" in " ".join(result.limitations).lower()


def test_projection_rejects_non_cost_sharing_finding() -> None:
    invalid = replace(_star_finding(), finding_type="DOCUMENTED_FACT")
    with pytest.raises(ConditionAssessmentProjectionError, match="CLAIM_COST_SHARING"):
        project_conditional_copayment_finding(invalid)


def test_projection_rejects_finding_without_trigger() -> None:
    invalid = replace(_star_finding(), trigger=None, condition=None)
    with pytest.raises(ConditionAssessmentProjectionError, match="trigger"):
        project_conditional_copayment_finding(invalid)


def test_projection_rejects_unsupported_rule_identity() -> None:
    invalid = replace(_star_finding(), rule_id="legacy_copay_rule")
    with pytest.raises(ConditionAssessmentProjectionError, match="unsupported"):
        project_conditional_copayment_finding(invalid)


def test_zero_copayment_is_very_strong_only_on_this_dimension() -> None:
    base = project_conditional_copayment_finding(_star_finding())
    zero = replace(base, projection_id="zero-copay", percentage=0.0)
    result = assess_conditional_copayment(zero)
    assert result.assessment_band is AssessmentBand.VERY_STRONG
    assert "overall" not in result.summary.lower()


def test_high_copayment_is_very_restrictive() -> None:
    base = project_conditional_copayment_finding(_star_finding())
    high = replace(base, projection_id="high-copay", percentage=30.0)
    result = assess_conditional_copayment(high)
    assert result.assessment_band is AssessmentBand.VERY_RESTRICTIVE


def test_projection_and_assessment_are_deterministic() -> None:
    first_projection = project_conditional_copayment_finding(_star_finding())
    second_projection = project_conditional_copayment_finding(_star_finding())
    assert first_projection == second_projection
    assert assess_conditional_copayment(first_projection) == assess_conditional_copayment(second_projection)


def test_copayment_assessment_has_no_rank_or_recommendation_surface() -> None:
    result = assess_conditional_copayment(
        project_conditional_copayment_finding(_star_finding())
    )
    forbidden = {
        "overall_score",
        "rank",
        "winner",
        "weight",
        "recommendation",
        "suitability",
    }
    assert forbidden.isdisjoint(result.__dataclass_fields__)
