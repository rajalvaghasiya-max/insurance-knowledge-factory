from datetime import date

from insurance_intelligence.benefits.catalogue import RESTORATION_BENEFIT_CONCEPT
from insurance_intelligence.benefits.star_comprehensive import (
    STAR_COMPREHENSIVE_PRODUCT_VARIANT_ID,
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
)


def _mechanics():
    return {
        item.dimension_id: item
        for item in STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.mechanics
    }


def test_restoration_concept_is_governed_and_active():
    assert RESTORATION_BENEFIT_CONCEPT.is_governed_for_use is True
    assert RESTORATION_BENEFIT_CONCEPT.is_active(date(2026, 7, 31)) is True


def test_star_implementation_is_governed_and_matches_variant():
    implementation = STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION
    assert implementation.is_governed_for_use is True
    assert implementation.product_variant_id == STAR_COMPREHENSIVE_PRODUCT_VARIANT_ID
    implementation.validate_against(RESTORATION_BENEFIT_CONCEPT)


def test_policy_and_prospectus_hashes_are_exact():
    evidence = {
        item.authority_type: item
        for item in STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.evidence_references
    }
    assert evidence["policy_wording"].source_sha256 == (
        "b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f"
    )
    assert evidence["prospectus"].source_sha256 == (
        "0404693147bd5202e28e39bfdb8fcc87f78e7ee6aa6a6f1032f63cbec63698e1"
    )


def test_restores_one_hundred_percent_once_after_full_exhaustion():
    mechanics = _mechanics()
    assert mechanics["restoration_percentage"].value == 100
    assert mechanics["restoration_count_per_policy_period"].value == 1
    assert mechanics["trigger_requirement"].value == (
        "exhaustion_of_basic_sum_insured_and_accrued_cumulative_bonus_if_any"
    )
    assert mechanics["trigger_timing"].value == "immediately_upon_exhaustion"


def test_restoration_is_for_subsequent_not_same_hospitalization():
    mechanics = _mechanics()
    assert mechanics["same_hospitalization_use"].value is False
    assert mechanics["subsequent_hospitalization_use"].value is True


def test_same_illness_is_allowed_but_relapse_rule_is_preserved():
    mechanics = _mechanics()
    assert mechanics["same_illness_use"].value is True
    assert mechanics["relapse_window_days"].value == 45
    assert "same hospitalization" in mechanics["relapse_window_days"].applicability["meaning"]


def test_covered_section_scope_is_exact():
    assert _mechanics()["covered_section_scope"].value == (
        "II.1, II.3, II.5, II.6, II.7, II.8 and II.11"
    )


def test_multi_year_and_floater_boundaries_are_preserved():
    mechanics = _mechanics()
    assert mechanics["policy_year_reset"].value is True
    assert mechanics["carry_over_between_policy_years"].value is False
    assert mechanics["floater_operation"].value == "floats_among_insured_persons"


def test_every_mechanic_has_known_evidence():
    implementation = STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION
    known_ids = {item.evidence_reference_id for item in implementation.evidence_references}
    assert known_ids
    for mechanic in implementation.mechanics:
        assert set(mechanic.evidence_reference_ids) <= known_ids


def test_behaviour_signature_is_stable_and_descriptive():
    assert STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.behaviour_signature_id == (
        "bsig:star_comprehensive:restoration:100pct_once_after_full_exhaustion_subsequent_hospitalization"
    )
