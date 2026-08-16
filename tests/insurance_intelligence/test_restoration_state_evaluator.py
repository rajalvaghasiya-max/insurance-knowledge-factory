from __future__ import annotations

import pytest

from insurance_intelligence.benefits.restoration_state import (
    RestorationClaimState,
    RestorationFrequencyBand,
    RestorationRuleParameters,
    RestorationStateContractError,
    evaluate_restoration_state,
)


INPATIENT = "INPATIENT_HOSPITALIZATION_TREATMENT"


def _bajaj_current_rule_shape() -> RestorationRuleParameters:
    """Current-source-qualified bounded Bajaj shape; unresolved facts stay unresolved."""
    return RestorationRuleParameters(
        rule_id="bajaj_mhc_current_restoration_bounded",
        activation_trigger_state="UNRESOLVED",
        activation_effective_point="SUBSEQUENT_CLAIM_ONLY",
        subsequent_claim_min_gap_days=15,
        other_beneficiary_gap_exempt=True,
        same_illness_subsequent_claim_rule="UNRESOLVED",
        different_illness_subsequent_claim_rule="UNRESOLVED",
        covered_section=INPATIENT,
        frequency_bands=(
            RestorationFrequencyBand(
                min_sum_insured_rupees=0,
                max_sum_insured_rupees=499_999,
                restoration_count_limit=1,
            ),
            RestorationFrequencyBand(
                min_sum_insured_rupees=500_000,
                max_sum_insured_rupees=None,
                restoration_count_limit=None,
            ),
        ),
    )


def _contrast_rule_shape() -> RestorationRuleParameters:
    """Synthetic conformance fixture with materially different state semantics."""
    return RestorationRuleParameters(
        rule_id="synthetic_within_triggering_claim_once",
        activation_trigger_state="RESOLVED",
        activation_effective_point="WITHIN_TRIGGERING_CLAIM",
        subsequent_claim_min_gap_days=0,
        other_beneficiary_gap_exempt=False,
        same_illness_subsequent_claim_rule="NOT_ALLOWED",
        different_illness_subsequent_claim_rule="ALLOWED",
        covered_section=INPATIENT,
        frequency_bands=(
            RestorationFrequencyBand(
                min_sum_insured_rupees=0,
                max_sum_insured_rupees=None,
                restoration_count_limit=1,
            ),
        ),
    )


def test_bajaj_triggering_claim_overflow_is_derived_not_eligible() -> None:
    result = evaluate_restoration_state(
        rule=_bajaj_current_rule_shape(),
        state=RestorationClaimState(
            sum_insured_rupees=1_000_000,
            claim_sequence="TRIGGERING",
            claim_section=INPATIENT,
            prior_restorations_used=0,
            activation_trigger_satisfied=None,
            illness_relationship="UNKNOWN",
        ),
    )

    assert result.status == "NOT_ELIGIBLE"
    assert result.frequency_unlimited is True
    assert "TRIGGERING_CLAIM_CANNOT_CONSUME_RESTORATION" in result.failed_conditions
    assert "ACTIVATION_TRIGGER_UNRESOLVED" in result.unresolved_conditions
    assert result.derived_reasons == (
        "Derived from activation_effective_point=SUBSEQUENT_CLAIM_ONLY.",
    )


def test_bajaj_subsequent_claim_remains_unresolved_when_trigger_and_illness_scope_are_unresolved() -> None:
    result = evaluate_restoration_state(
        rule=_bajaj_current_rule_shape(),
        state=RestorationClaimState(
            sum_insured_rupees=1_000_000,
            claim_sequence="SUBSEQUENT",
            claim_section=INPATIENT,
            prior_restorations_used=0,
            activation_trigger_satisfied=None,
            days_since_prior_discharge=20,
            illness_relationship="SAME",
        ),
    )

    assert result.status == "UNRESOLVED"
    assert result.frequency_unlimited is True
    assert result.failed_conditions == ()
    assert set(result.unresolved_conditions) == {
        "ACTIVATION_TRIGGER_UNRESOLVED",
        "ILLNESS_RELATIONSHIP_RULE_UNRESOLVED",
    }


def test_bajaj_frequency_band_can_fail_closed_independently_of_unresolved_trigger() -> None:
    result = evaluate_restoration_state(
        rule=_bajaj_current_rule_shape(),
        state=RestorationClaimState(
            sum_insured_rupees=400_000,
            claim_sequence="SUBSEQUENT",
            claim_section=INPATIENT,
            prior_restorations_used=1,
            activation_trigger_satisfied=None,
            days_since_prior_discharge=20,
            illness_relationship="DIFFERENT",
        ),
    )

    assert result.status == "NOT_ELIGIBLE"
    assert result.selected_frequency_limit == 1
    assert result.frequency_unlimited is False
    assert "RESTORATION_FREQUENCY_EXHAUSTED" in result.failed_conditions


def test_same_generic_evaluator_executes_materially_different_contrast_rule() -> None:
    result = evaluate_restoration_state(
        rule=_contrast_rule_shape(),
        state=RestorationClaimState(
            sum_insured_rupees=1_000_000,
            claim_sequence="TRIGGERING",
            claim_section=INPATIENT,
            prior_restorations_used=0,
            activation_trigger_satisfied=True,
            illness_relationship="DIFFERENT",
        ),
    )

    assert result.status == "ELIGIBLE"
    assert result.selected_frequency_limit == 1
    assert result.frequency_unlimited is False
    assert result.failed_conditions == ()
    assert result.unresolved_conditions == ()


def test_contrast_rule_changes_only_data_for_same_illness_subsequent_claim() -> None:
    result = evaluate_restoration_state(
        rule=_contrast_rule_shape(),
        state=RestorationClaimState(
            sum_insured_rupees=1_000_000,
            claim_sequence="SUBSEQUENT",
            claim_section=INPATIENT,
            prior_restorations_used=0,
            activation_trigger_satisfied=True,
            days_since_prior_discharge=1,
            illness_relationship="SAME",
        ),
    )

    assert result.status == "NOT_ELIGIBLE"
    assert result.failed_conditions == ("ILLNESS_RELATIONSHIP_NOT_ALLOWED",)


def test_closed_vocabulary_rejects_embedded_activation_expression() -> None:
    with pytest.raises(RestorationStateContractError):
        RestorationRuleParameters(
            rule_id="expression_smuggling_attempt",
            activation_trigger_state="RESOLVED",
            activation_effective_point=(
                "if base_si_exhausted and previous_restorations < 1 then activate"
            ),
            subsequent_claim_min_gap_days=0,
            other_beneficiary_gap_exempt=False,
            same_illness_subsequent_claim_rule="ALLOWED",
            different_illness_subsequent_claim_rule="ALLOWED",
            covered_section=INPATIENT,
            frequency_bands=(
                RestorationFrequencyBand(
                    min_sum_insured_rupees=0,
                    max_sum_insured_rupees=None,
                    restoration_count_limit=1,
                ),
            ),
        )


def test_overlapping_frequency_bands_are_rejected() -> None:
    with pytest.raises(RestorationStateContractError):
        RestorationRuleParameters(
            rule_id="overlap",
            activation_trigger_state="RESOLVED",
            activation_effective_point="SUBSEQUENT_CLAIM_ONLY",
            subsequent_claim_min_gap_days=0,
            other_beneficiary_gap_exempt=False,
            same_illness_subsequent_claim_rule="ALLOWED",
            different_illness_subsequent_claim_rule="ALLOWED",
            covered_section=INPATIENT,
            frequency_bands=(
                RestorationFrequencyBand(0, 500_000, 1),
                RestorationFrequencyBand(500_000, None, None),
            ),
        )
