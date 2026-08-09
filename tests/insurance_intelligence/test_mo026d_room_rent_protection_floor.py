import pytest

from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentBand,
    AssessmentStatus,
    DecisionRole,
    InteractionSeverity,
    InteractionType,
)
from insurance_intelligence.benefits.room_rent_assessment import (
    GovernedRoomRentRestriction,
    ProportionateDeductionStatus,
    RoomRentAssessmentError,
    RoomRentCapType,
    assess_room_rent_restriction,
)


def restriction(**changes):
    base = dict(
        restriction_id="rr:test:1",
        product_reference="test_insurer:test_product",
        cap_type=RoomRentCapType.ROOM_CATEGORY,
        cap_value=None,
        eligible_room_category="single private room",
        icu_rule="ICU as per policy terms",
        proportionate_deduction=ProportionateDeductionStatus.DOES_NOT_APPLY,
        proportionate_deduction_scope=None,
        exceptions=(),
        evidence_reference_ids=("ev-room-rent-1",),
        governed_source_type="CONTROLLED_CERTIFICATION_FIXTURE",
    )
    base.update(changes)
    return GovernedRoomRentRestriction(**base)


def test_no_room_rent_limit_is_very_strong_on_this_dimension_only() -> None:
    result = assess_room_rent_restriction(
        restriction(
            cap_type=RoomRentCapType.NO_LIMIT,
            cap_value=None,
            eligible_room_category=None,
        )
    )
    assert result.status is AssessmentStatus.ASSESSED_WITH_LIMITATIONS
    assert result.assessment_band is AssessmentBand.VERY_STRONG
    assert result.decision_role is DecisionRole.PROTECTION_FLOOR
    assert "No governed room-rent cap" in result.summary


def test_room_cap_without_proportionate_deduction_is_restrictive() -> None:
    result = assess_room_rent_restriction(restriction())
    assert result.assessment_band is AssessmentBand.RESTRICTIVE
    assert result.interaction_references == ()
    assert "not applying" in result.summary


def test_room_cap_with_proportionate_deduction_is_very_restrictive() -> None:
    result = assess_room_rent_restriction(
        restriction(
            proportionate_deduction=ProportionateDeductionStatus.APPLIES,
            proportionate_deduction_scope="associated hospitalization expenses",
        )
    )
    assert result.assessment_band is AssessmentBand.VERY_RESTRICTIVE
    assert result.has_material_interaction is True
    interaction = result.interaction_references[0]
    assert interaction.target_dimension_id == "restoration"
    assert interaction.interaction_type is InteractionType.MAY_REDUCE_EFFECT
    assert interaction.severity is InteractionSeverity.CRITICAL
    assert "admissible hospitalization expenses" in interaction.explanation


def test_unknown_proportionate_deduction_fails_closed() -> None:
    result = assess_room_rent_restriction(
        restriction(
            proportionate_deduction=ProportionateDeductionStatus.UNKNOWN,
        )
    )
    assert result.status is AssessmentStatus.NOT_SCORABLE
    assert result.assessment_band is None
    assert "unresolved" in result.limitations[0].lower()


def test_applies_requires_governed_scope() -> None:
    with pytest.raises(RoomRentAssessmentError, match="requires proportionate_deduction_scope"):
        restriction(
            proportionate_deduction=ProportionateDeductionStatus.APPLIES,
            proportionate_deduction_scope=None,
        )


def test_room_category_requires_category_value() -> None:
    with pytest.raises(RoomRentAssessmentError, match="eligible_room_category"):
        restriction(eligible_room_category=None)


def test_fixed_daily_cap_requires_cap_value() -> None:
    with pytest.raises(RoomRentAssessmentError, match="require cap_value"):
        restriction(
            cap_type=RoomRentCapType.FIXED_DAILY_AMOUNT,
            cap_value=None,
            eligible_room_category=None,
        )


def test_evidence_lineage_is_mandatory() -> None:
    with pytest.raises(RoomRentAssessmentError, match="non-empty tuple"):
        restriction(evidence_reference_ids=())


def test_exact_contract_type_is_required() -> None:
    with pytest.raises(RoomRentAssessmentError, match="exact GovernedRoomRentRestriction"):
        assess_room_rent_restriction({"room_rent_limit": "single private room"})  # type: ignore[arg-type]


def test_assessment_has_no_ranking_or_recommendation_surface() -> None:
    result = assess_room_rent_restriction(restriction())
    forbidden = {
        "overall_score",
        "rank",
        "winner",
        "weight",
        "recommendation",
        "suitability",
    }
    assert forbidden.isdisjoint(result.__dataclass_fields__)


def test_pd_interaction_does_not_predict_claim_amount() -> None:
    result = assess_room_rent_restriction(
        restriction(
            proportionate_deduction=ProportionateDeductionStatus.APPLIES,
            proportionate_deduction_scope="associated hospitalization expenses",
        )
    )
    text = " ".join(
        [result.summary, result.practical_meaning]
        + [item.explanation for item in result.interaction_references]
    ).lower()
    assert "expected claim" not in text
    assert "₹" not in text
    assert "predict" not in result.summary.lower()


def test_controlled_fixture_is_not_claimed_as_real_product_publication() -> None:
    item = restriction()
    assert item.governed_source_type == "CONTROLLED_CERTIFICATION_FIXTURE"
    assert "star_health" not in item.product_reference
    assert "aditya_birla_health" not in item.product_reference
