from dataclasses import replace
from datetime import date

import pytest

from insurance_intelligence.benefits.activ_one_nxt import (
    ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentBand,
    AssessmentStatus,
    DecisionRole,
)
from insurance_intelligence.benefits.assessment_engine import (
    BenefitAssessmentEngineError,
    assess_product_benefit,
)
from insurance_intelligence.benefits.assessment_policies import (
    AssessmentCriterion,
    AssessmentPolicyError,
    CriterionOperator,
)
from insurance_intelligence.benefits.assessment_taxonomy import RESTORATION_DIMENSION
from insurance_intelligence.benefits.contracts import PublicationStatus
from insurance_intelligence.benefits.restoration_assessment_policy import (
    RESTORATION_ASSESSMENT_POLICY,
)
from insurance_intelligence.benefits.star_comprehensive import (
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
)


def _assess(implementation):
    return assess_product_benefit(
        implementation=implementation,
        dimension=RESTORATION_DIMENSION,
        policy=RESTORATION_ASSESSMENT_POLICY,
    )


def test_restoration_policy_is_governed_and_active() -> None:
    policy = RESTORATION_ASSESSMENT_POLICY
    assert policy.is_governed_for_use is True
    assert policy.is_active(date(2026, 8, 9)) is True
    assert policy.dimension_id == "restoration"
    assert policy.policy_version == "1.0"


def test_policy_declares_required_restoration_mechanics() -> None:
    assert RESTORATION_ASSESSMENT_POLICY.required_mechanic_ids == (
        "restoration_percentage",
        "restoration_count_per_policy_period",
        "trigger_requirement",
        "same_hospitalization_use",
        "subsequent_hospitalization_use",
    )


def test_policy_carries_explicit_governance_basis() -> None:
    text = RESTORATION_ASSESSMENT_POLICY.governance_basis.lower()
    assert "policy choice" in text
    assert "overall product score" in text
    assert "suitability" in text


def test_activ_one_nxt_restoration_is_very_strong_on_intrinsic_mechanics() -> None:
    result = _assess(ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION)
    assert result.status is AssessmentStatus.ASSESSED_WITH_LIMITATIONS
    assert result.assessment_band is AssessmentBand.VERY_STRONG
    assert result.decision_role is DecisionRole.CORE_PROTECTION
    assert result.assessment_policy_id == RESTORATION_ASSESSMENT_POLICY.policy_id
    assert result.assessment_policy_version == "1.0"


def test_star_restoration_is_strong_not_very_strong() -> None:
    result = _assess(STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION)
    assert result.status is AssessmentStatus.ASSESSED_WITH_LIMITATIONS
    assert result.assessment_band is AssessmentBand.STRONG
    assert "subsequent-hospitalization" in result.summary.lower()


def test_assessment_preserves_required_mechanic_lineage() -> None:
    result = _assess(ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION)
    assert result.source_mechanic_ids == RESTORATION_ASSESSMENT_POLICY.required_mechanic_ids
    assert result.evidence_reference_ids
    known = {
        item.evidence_reference_id
        for item in ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.evidence_references
    }
    assert set(result.evidence_reference_ids) <= known


def test_assessment_preserves_implementation_limitations() -> None:
    result = _assess(STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION)
    assert result.limitations == STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.limitations


def test_missing_required_mechanic_fails_closed_as_not_scorable() -> None:
    incomplete = replace(
        ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
        implementation_id="benefit_impl:test:restoration:missing-trigger",
        mechanics=tuple(
            item
            for item in ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.mechanics
            if item.dimension_id != "trigger_requirement"
        ),
    )
    result = _assess(incomplete)
    assert result.status is AssessmentStatus.NOT_SCORABLE
    assert result.assessment_band is None
    assert "trigger_requirement" in " ".join(result.limitations)


def test_unmatched_governed_combination_fails_closed() -> None:
    mechanics = tuple(
        replace(item, value=50)
        if item.dimension_id == "restoration_percentage"
        else replace(item, value=False)
        if item.dimension_id == "subsequent_hospitalization_use"
        else item
        for item in ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.mechanics
    )
    variant = replace(
        ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
        implementation_id="benefit_impl:test:restoration:unmatched",
        mechanics=mechanics,
    )
    result = _assess(variant)
    assert result.status is AssessmentStatus.MODERATE if False else AssessmentStatus.NOT_SCORABLE
    assert result.assessment_band is None
    assert "no published assessment rule" in result.limitations[0].lower()


def test_assessment_is_reproducible() -> None:
    assert _assess(ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION) == _assess(
        ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION
    )


def test_assessment_has_no_ranking_or_recommendation_surface() -> None:
    result = _assess(ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION)
    forbidden = {
        "overall_score",
        "rank",
        "winner",
        "weight",
        "recommendation",
        "suitability",
    }
    assert forbidden.isdisjoint(result.__dataclass_fields__)


def test_engine_rejects_unpublished_policy() -> None:
    unpublished = replace(
        RESTORATION_ASSESSMENT_POLICY,
        publication_status=PublicationStatus.NOT_PUBLISHED,
    )
    with pytest.raises(BenefitAssessmentEngineError, match="assessment policy"):
        assess_product_benefit(
            implementation=ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
            dimension=RESTORATION_DIMENSION,
            policy=unpublished,
        )


def test_present_criterion_cannot_carry_expected_value() -> None:
    with pytest.raises(AssessmentPolicyError, match="cannot carry"):
        AssessmentCriterion(
            mechanic_id="trigger_requirement",
            operator=CriterionOperator.PRESENT,
            expected_value=True,
            rationale="invalid criterion",
        )
