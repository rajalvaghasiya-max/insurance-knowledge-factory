import pytest

from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentBand,
    AssessmentStatus,
    BenefitAssessment,
    BenefitAssessmentContractError,
    BenefitInteractionReference,
    DecisionRole,
    InteractionSeverity,
    InteractionType,
)


def _interaction(**overrides):
    values = {
        "target_dimension_id": "restoration",
        "interaction_type": InteractionType.MAY_REDUCE_EFFECT,
        "severity": InteractionSeverity.MATERIAL,
        "explanation": "Room-rent-linked proportionate deduction may reduce admissible hospitalization expenses before restoration is reached.",
        "source_mechanic_ids": ("room_rent_limit", "proportionate_deduction"),
        "evidence_reference_ids": ("ev-policy",),
    }
    values.update(overrides)
    return BenefitInteractionReference(**values)


def _assessment(**overrides):
    values = {
        "assessment_id": "assessment:test:copay:v1",
        "implementation_id": "benefit_impl:test:copay:v1",
        "concept_id": "health:cost_sharing:copayment",
        "dimension_id": "copayment",
        "decision_role": DecisionRole.PROTECTION_FLOOR,
        "status": AssessmentStatus.ASSESSED,
        "assessment_band": AssessmentBand.RESTRICTIVE,
        "assessment_policy_id": "assessment_policy:health:copayment:v1",
        "assessment_policy_version": "1.0",
        "summary": "The policy contains a material copayment obligation.",
        "practical_meaning": "The insured may have to bear part of the admissible claim amount when the governed condition applies.",
        "source_mechanic_ids": ("copayment_percentage", "copayment_trigger"),
        "evidence_reference_ids": ("ev-policy",),
        "limitations": (),
        "interaction_references": (),
    }
    values.update(overrides)
    return BenefitAssessment(**values)


def test_assessed_contract_preserves_governed_policy_identity():
    result = _assessment()
    assert result.status is AssessmentStatus.ASSESSED
    assert result.assessment_band is AssessmentBand.RESTRICTIVE
    assert result.assessment_policy_id == "assessment_policy:health:copayment:v1"
    assert result.assessment_policy_version == "1.0"
    assert result.is_assessed is True


def test_protection_floor_is_explicit_and_queryable():
    result = _assessment()
    assert result.decision_role is DecisionRole.PROTECTION_FLOOR
    assert result.is_protection_floor is True


def test_price_is_a_distinct_decision_role():
    result = _assessment(
        assessment_id="assessment:test:price:v1",
        dimension_id="premium",
        decision_role=DecisionRole.PRICE,
        assessment_band=AssessmentBand.MODERATE,
        assessment_policy_id="assessment_policy:health:quote_price:v1",
        summary="Quoted premium is assessed only on a comparable quote basis.",
        practical_meaning="Price is kept distinct from insurance-quality assessment.",
        source_mechanic_ids=("quote_final_premium",),
    )
    assert result.decision_role is DecisionRole.PRICE
    assert result.is_protection_floor is False


def test_not_scorable_requires_no_band_and_an_explanation():
    result = _assessment(
        status=AssessmentStatus.NOT_SCORABLE,
        assessment_band=None,
        assessment_policy_id=None,
        assessment_policy_version=None,
        limitations=("The governed copayment trigger is unresolved.",),
    )
    assert result.status is AssessmentStatus.NOT_SCORABLE
    assert result.assessment_band is None
    assert result.is_assessed is False


def test_not_scorable_without_limitation_fails_closed():
    with pytest.raises(BenefitAssessmentContractError, match="NOT_SCORABLE"):
        _assessment(
            status=AssessmentStatus.NOT_SCORABLE,
            assessment_band=None,
            assessment_policy_id=None,
            assessment_policy_version=None,
            limitations=(),
        )


def test_not_scorable_cannot_carry_a_strength_band():
    with pytest.raises(BenefitAssessmentContractError, match="cannot carry"):
        _assessment(
            status=AssessmentStatus.NOT_SCORABLE,
            assessment_band=AssessmentBand.MODERATE,
            assessment_policy_id=None,
            assessment_policy_version=None,
            limitations=("Missing governed evidence.",),
        )


def test_assessed_status_requires_a_band():
    with pytest.raises(BenefitAssessmentContractError, match="assessment_band"):
        _assessment(assessment_band=None)


def test_assessed_status_requires_versioned_policy():
    with pytest.raises(BenefitAssessmentContractError, match="policy identity"):
        _assessment(assessment_policy_id=None)
    with pytest.raises(BenefitAssessmentContractError, match="policy identity"):
        _assessment(assessment_policy_version=None)


def test_assessed_with_limitations_requires_limitations():
    with pytest.raises(BenefitAssessmentContractError, match="requires at least one limitation"):
        _assessment(status=AssessmentStatus.ASSESSED_WITH_LIMITATIONS, limitations=())


def test_interaction_reference_preserves_mechanic_and_evidence_lineage():
    interaction = _interaction()
    assert interaction.target_dimension_id == "restoration"
    assert interaction.source_mechanic_ids == (
        "room_rent_limit",
        "proportionate_deduction",
    )
    assert interaction.evidence_reference_ids == ("ev-policy",)


def test_material_interaction_is_visible_on_assessment():
    result = _assessment(interaction_references=(_interaction(),))
    assert result.has_material_interaction is True


def test_informational_interaction_does_not_trigger_material_flag():
    result = _assessment(
        interaction_references=(
            _interaction(severity=InteractionSeverity.INFORMATIONAL),
        )
    )
    assert result.has_material_interaction is False


def test_interaction_requires_nonempty_source_mechanics_and_evidence():
    with pytest.raises(BenefitAssessmentContractError, match="source_mechanic_ids"):
        _interaction(source_mechanic_ids=())
    with pytest.raises(BenefitAssessmentContractError, match="evidence_reference_ids"):
        _interaction(evidence_reference_ids=())


def test_assessment_requires_nonempty_source_mechanics_and_evidence():
    with pytest.raises(BenefitAssessmentContractError, match="source_mechanic_ids"):
        _assessment(source_mechanic_ids=())
    with pytest.raises(BenefitAssessmentContractError, match="evidence_reference_ids"):
        _assessment(evidence_reference_ids=())


def test_duplicate_lineage_ids_are_rejected():
    with pytest.raises(BenefitAssessmentContractError, match="duplicates"):
        _assessment(source_mechanic_ids=("copayment_percentage", "copayment_percentage"))
    with pytest.raises(BenefitAssessmentContractError, match="duplicates"):
        _interaction(evidence_reference_ids=("ev-policy", "ev-policy"))


def test_no_contract_field_encodes_product_winner_or_recommendation():
    fields = set(BenefitAssessment.__dataclass_fields__)
    forbidden = {
        "overall_score",
        "rank",
        "winner",
        "recommended_product_id",
        "recommendation",
        "suitability_score",
        "weight",
    }
    assert fields.isdisjoint(forbidden)


def test_decision_roles_are_explicit_and_closed():
    assert tuple(item.value for item in DecisionRole) == (
        "PROTECTION_FLOOR",
        "CORE_PROTECTION",
        "PREFERENCE",
        "CONTEXT_DEPENDENT",
        "PRICE",
    )


def test_assessment_bands_are_qualitative_not_numeric():
    assert tuple(item.value for item in AssessmentBand) == (
        "VERY_STRONG",
        "STRONG",
        "MODERATE",
        "RESTRICTIVE",
        "VERY_RESTRICTIVE",
    )
