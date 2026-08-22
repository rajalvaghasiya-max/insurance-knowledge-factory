import pytest

from insurance_intelligence.benefits.waiting_period_contracts import (
    WaitingPeriodContractError,
    WaitingPeriodDurationUnit,
    WaitingPeriodMechanic,
    WaitingPeriodModification,
    WaitingPeriodModificationType,
    WaitingPeriodStartBasis,
    WaitingPeriodSumInsuredEnhancementEffect,
    WaitingPeriodType,
)


def _base_mechanic(**overrides):
    values = dict(
        waiting_period_type=WaitingPeriodType.PRE_EXISTING_DISEASE,
        duration_value=36,
        duration_unit=WaitingPeriodDurationUnit.MONTHS,
        start_basis=WaitingPeriodStartBasis.INSURED_PERSON_FIRST_COVERAGE,
        applies_to=("pre_existing_disease",),
        evidence_reference_ids=("ev_waiting_period_policy_wording",),
    )
    values.update(overrides)
    return WaitingPeriodMechanic(**values)


def test_supports_material_waiting_period_types():
    assert tuple(item.value for item in WaitingPeriodType) == (
        "INITIAL",
        "SPECIFIC_DISEASE_PROCEDURE",
        "PRE_EXISTING_DISEASE",
        "MATERNITY",
        "BABY_CARE",
        "BENEFIT_SPECIFIC",
    )


def test_base_waiting_period_requires_evidence():
    with pytest.raises(WaitingPeriodContractError, match="requires evidence"):
        _base_mechanic(evidence_reference_ids=())


def test_applies_to_scope_cannot_be_empty():
    with pytest.raises(WaitingPeriodContractError, match="applies_to must not be empty"):
        _base_mechanic(applies_to=())


def test_duration_must_be_non_negative_integer():
    with pytest.raises(WaitingPeriodContractError, match="non-negative integer"):
        _base_mechanic(duration_value=-1)


def test_policy_schedule_start_requires_schedule_dependency():
    with pytest.raises(WaitingPeriodContractError, match="schedule_dependency"):
        _base_mechanic(start_basis=WaitingPeriodStartBasis.POLICY_SCHEDULE_DEFINED)


def test_continuous_coverage_start_requires_continuity_dependency():
    with pytest.raises(WaitingPeriodContractError, match="continuity_dependency"):
        _base_mechanic(start_basis=WaitingPeriodStartBasis.CONTINUOUS_COVERAGE)


def test_waiting_period_preserves_exceptions_separately_from_scope():
    mechanic = _base_mechanic(
        exclusions_or_exceptions=("accident_related_hospitalization",),
    )
    assert mechanic.applies_to == ("pre_existing_disease",)
    assert mechanic.exclusions_or_exceptions == ("accident_related_hospitalization",)


def test_sum_insured_enhancement_reapplication_is_typed_separately():
    mechanic = _base_mechanic(
        sum_insured_enhancement_effect=(
            WaitingPeriodSumInsuredEnhancementEffect.REAPPLIES_TO_ENHANCED_PORTION
        ),
    )
    assert mechanic.sum_insured_enhancement_effect is (
        WaitingPeriodSumInsuredEnhancementEffect.REAPPLIES_TO_ENHANCED_PORTION
    )


def test_sum_insured_enhancement_effect_rejects_untyped_text():
    with pytest.raises(WaitingPeriodContractError, match="sum_insured_enhancement_effect"):
        _base_mechanic(sum_insured_enhancement_effect="REAPPLIES_TO_ENHANCED_PORTION")


def test_waiver_can_remove_waiting_period_without_fake_duration():
    modification = WaitingPeriodModification(
        modification_type=WaitingPeriodModificationType.WAIVER,
        condition="specified waiver condition applies",
        evidence_reference_ids=("ev_waiver",),
    )
    assert modification.resulting_duration_value is None


def test_reduction_requires_resulting_duration():
    with pytest.raises(WaitingPeriodContractError, match="requires a resulting duration"):
        WaitingPeriodModification(
            modification_type=WaitingPeriodModificationType.REDUCTION,
            condition="optional reduction selected",
            evidence_reference_ids=("ev_reduction",),
        )


def test_reduction_preserves_resulting_duration_and_evidence():
    modification = WaitingPeriodModification(
        modification_type=WaitingPeriodModificationType.REDUCTION,
        condition="optional reduction selected",
        resulting_duration_value=24,
        resulting_duration_unit=WaitingPeriodDurationUnit.MONTHS,
        evidence_reference_ids=("ev_reduction",),
    )
    mechanic = _base_mechanic(modifications=(modification,))
    assert mechanic.duration_value == 36
    assert mechanic.modifications[0].resulting_duration_value == 24


def test_modification_requires_evidence():
    with pytest.raises(WaitingPeriodContractError, match="requires evidence"):
        WaitingPeriodModification(
            modification_type=WaitingPeriodModificationType.WAIVER,
            condition="waiver applies",
            evidence_reference_ids=(),
        )


def test_contract_has_no_recommendation_or_claim_payment_fields():
    forbidden = {
        "score",
        "rating",
        "rank",
        "winner",
        "recommendation",
        "suitability",
        "claim_payment",
        "claim_admissibility",
    }
    fields = set(WaitingPeriodMechanic.__dataclass_fields__)
    assert forbidden.isdisjoint(fields)
