from __future__ import annotations

from insurance_intelligence.benefits.restoration_state import (
    RestorationClaimState,
    RestorationFrequencyBand,
    RestorationRuleParameters,
    evaluate_restoration_state,
)


def _activ_one_rule() -> RestorationRuleParameters:
    return RestorationRuleParameters(
        rule_id="activ_one_current_super_reload",
        activation_trigger_state="RESOLVED",
        activation_effective_point="WITHIN_TRIGGERING_CLAIM",
        subsequent_claim_min_gap_days=None,
        other_beneficiary_gap_exempt=False,
        same_illness_subsequent_claim_rule="ALLOWED",
        different_illness_subsequent_claim_rule="ALLOWED",
        covered_section="C.1_HOSPITALIZATION_TREATMENT",
        frequency_bands=(
            RestorationFrequencyBand(
                min_sum_insured_rupees=0,
                max_sum_insured_rupees=None,
                restoration_count_limit=None,
            ),
        ),
    )


def test_current_activ_one_same_triggering_claim_shape_executes_without_evaluator_change() -> None:
    result = evaluate_restoration_state(
        rule=_activ_one_rule(),
        state=RestorationClaimState(
            sum_insured_rupees=1_000_000,
            claim_sequence="TRIGGERING",
            claim_section="C.1_HOSPITALIZATION_TREATMENT",
            prior_restorations_used=0,
            activation_trigger_satisfied=True,
            illness_relationship="SAME",
        ),
    )

    assert result.status == "ELIGIBLE"
    assert result.frequency_unlimited is True
    assert result.failed_conditions == ()


def test_current_activ_one_subsequent_claim_remains_eligible_when_trigger_satisfied() -> None:
    result = evaluate_restoration_state(
        rule=_activ_one_rule(),
        state=RestorationClaimState(
            sum_insured_rupees=1_000_000,
            claim_sequence="SUBSEQUENT",
            claim_section="C.1_HOSPITALIZATION_TREATMENT",
            prior_restorations_used=3,
            activation_trigger_satisfied=True,
            illness_relationship="DIFFERENT",
        ),
    )

    assert result.status == "ELIGIBLE"
    assert result.frequency_unlimited is True


def test_current_activ_one_positive_result_fails_closed_when_trigger_not_satisfied() -> None:
    result = evaluate_restoration_state(
        rule=_activ_one_rule(),
        state=RestorationClaimState(
            sum_insured_rupees=1_000_000,
            claim_sequence="TRIGGERING",
            claim_section="C.1_HOSPITALIZATION_TREATMENT",
            prior_restorations_used=0,
            activation_trigger_satisfied=False,
            illness_relationship="SAME",
        ),
    )

    assert result.status == "NOT_ELIGIBLE"
    assert "ACTIVATION_TRIGGER_NOT_SATISFIED" in result.failed_conditions


def test_current_activ_one_wrong_covered_section_is_not_eligible() -> None:
    result = evaluate_restoration_state(
        rule=_activ_one_rule(),
        state=RestorationClaimState(
            sum_insured_rupees=1_000_000,
            claim_sequence="TRIGGERING",
            claim_section="UNRELATED_OPTIONAL_COVER",
            prior_restorations_used=0,
            activation_trigger_satisfied=True,
            illness_relationship="SAME",
        ),
    )

    assert result.status == "NOT_ELIGIBLE"
    assert "CLAIM_SECTION_NOT_COVERED" in result.failed_conditions


def test_real_cross_insurer_shape_difference_is_executable_without_identity_branching() -> None:
    activ_rule = _activ_one_rule()

    triggering = evaluate_restoration_state(
        rule=activ_rule,
        state=RestorationClaimState(
            sum_insured_rupees=1_000_000,
            claim_sequence="TRIGGERING",
            claim_section="C.1_HOSPITALIZATION_TREATMENT",
            prior_restorations_used=0,
            activation_trigger_satisfied=True,
            illness_relationship="SAME",
        ),
    )

    # Activ One's current rule shape permits same-triggering-claim execution when
    # its governed trigger is satisfied. The earlier Bajaj gate established the
    # opposite shape (SUBSEQUENT_CLAIM_ONLY) through the same evaluator.
    assert triggering.status == "ELIGIBLE"
