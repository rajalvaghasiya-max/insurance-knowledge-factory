import pytest

from insurance_intelligence.benefits.assessment_contracts import DecisionRole
from insurance_intelligence.benefits.assessment_taxonomy import (
    AssessmentDimensionDefinition,
    AssessmentTaxonomyError,
    COPAYMENT_DIMENSION,
    DimensionFamily,
    PREMIUM_DIMENSION,
    RESTORATION_DIMENSION,
    ROOM_RENT_DIMENSION,
    registered_health_assessment_dimensions,
)


def test_registry_is_deterministic_and_unique():
    dimensions = registered_health_assessment_dimensions()
    ids = tuple(item.dimension_id for item in dimensions)
    assert ids == tuple(sorted(ids))
    assert len(ids) == len(set(ids))
    assert registered_health_assessment_dimensions() == dimensions


def test_initial_health_taxonomy_contains_core_education_dimensions():
    ids = {item.dimension_id for item in registered_health_assessment_dimensions()}
    assert {
        "copayment",
        "room_rent_restriction",
        "deductible",
        "procedure_or_disease_sublimit",
        "ped_waiting_period",
        "specific_disease_waiting_period",
        "restoration",
        "consumables_non_payables",
        "home_healthcare",
        "ayush",
        "network_access",
        "quoted_premium",
    } <= ids


def test_financial_restrictions_are_not_flat_preference_dimensions():
    for dimension in (COPAYMENT_DIMENSION, ROOM_RENT_DIMENSION):
        assert dimension.family is DimensionFamily.FINANCIAL_RESTRICTION
        assert dimension.decision_role is DecisionRole.PROTECTION_FLOOR
        assert dimension.non_suppressible_warning is True
        assert dimension.interaction_aware is True


def test_copayment_taxonomy_preserves_trigger_exception_and_scope_hooks():
    assert COPAYMENT_DIMENSION.source_mechanic_ids == (
        "copayment_percentage",
        "copayment_trigger",
        "copayment_exception",
        "copayment_scope",
    )


def test_room_rent_taxonomy_includes_proportionate_deduction_hooks():
    assert "proportionate_deduction" in ROOM_RENT_DIMENSION.source_mechanic_ids
    assert "proportionate_deduction_scope" in ROOM_RENT_DIMENSION.source_mechanic_ids


def test_restoration_is_core_protection_and_interaction_aware():
    assert RESTORATION_DIMENSION.family is DimensionFamily.COVERAGE_CAPACITY
    assert RESTORATION_DIMENSION.decision_role is DecisionRole.CORE_PROTECTION
    assert RESTORATION_DIMENSION.interaction_aware is True
    assert "trigger_requirement" in RESTORATION_DIMENSION.source_mechanic_ids
    assert "same_hospitalization_use" in RESTORATION_DIMENSION.source_mechanic_ids


def test_premium_is_separate_price_family_not_quality_dimension():
    assert PREMIUM_DIMENSION.family is DimensionFamily.PRICE
    assert PREMIUM_DIMENSION.decision_role is DecisionRole.PRICE
    assert PREMIUM_DIMENSION.source_mechanic_ids == ("quote_final_premium",)


def test_protection_floor_must_be_non_suppressible():
    with pytest.raises(AssessmentTaxonomyError, match="non_suppressible_warning"):
        AssessmentDimensionDefinition(
            dimension_id="test_protection_floor",
            canonical_name="Test",
            definition="Test protection dimension.",
            family=DimensionFamily.FINANCIAL_RESTRICTION,
            decision_role=DecisionRole.PROTECTION_FLOOR,
            source_mechanic_ids=("test_mechanic",),
            non_suppressible_warning=False,
        )


def test_price_role_and_family_must_match():
    with pytest.raises(AssessmentTaxonomyError, match="PRICE decision role"):
        AssessmentDimensionDefinition(
            dimension_id="bad_price_role",
            canonical_name="Bad price",
            definition="Invalid price role.",
            family=DimensionFamily.COVERAGE_FEATURE,
            decision_role=DecisionRole.PRICE,
            source_mechanic_ids=("quote_final_premium",),
        )
    with pytest.raises(AssessmentTaxonomyError, match="PRICE family"):
        AssessmentDimensionDefinition(
            dimension_id="bad_price_family",
            canonical_name="Bad price",
            definition="Invalid price family.",
            family=DimensionFamily.PRICE,
            decision_role=DecisionRole.PREFERENCE,
            source_mechanic_ids=("quote_final_premium",),
        )


def test_taxonomy_contains_no_weight_or_overall_score_contract():
    fields = set(AssessmentDimensionDefinition.__dataclass_fields__)
    assert fields.isdisjoint(
        {
            "weight",
            "default_weight",
            "overall_score",
            "rank",
            "winner",
            "recommendation",
        }
    )
