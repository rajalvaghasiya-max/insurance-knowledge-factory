from __future__ import annotations

from insurance_intelligence.benefits.star_comprehensive_waiting_periods import (
    STAR_COMPREHENSIVE_WAITING_PERIOD_PUBLICATION,
    WaitingPeriodPublicationReviewStatus,
    WaitingPeriodPublicationStatus,
)
from insurance_intelligence.benefits.waiting_period_contracts import (
    WaitingPeriodDurationUnit,
    WaitingPeriodModificationType,
    WaitingPeriodStartBasis,
    WaitingPeriodType,
)
from insurance_intelligence.coverage_registry.health_seed import STAR_COMPREHENSIVE_COVERAGE


def _by_type(waiting_period_type: WaitingPeriodType):
    return next(
        item
        for item in STAR_COMPREHENSIVE_WAITING_PERIOD_PUBLICATION.mechanics
        if item.waiting_period_type is waiting_period_type
    )


def test_publication_identity_and_governance_are_exact() -> None:
    publication = STAR_COMPREHENSIVE_WAITING_PERIOD_PUBLICATION
    assert publication.product_variant_id == "pv_star_health_star_comprehensive_shahlip26044v092526"
    assert publication.product_uin == "SHAHLIP26044V092526"
    assert publication.source_document_id == "star_health_star_comprehensive_policy_wording_v1"
    assert publication.source_document_sha256 == "b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f"
    assert publication.review_status is WaitingPeriodPublicationReviewStatus.APPROVED
    assert publication.publication_status is WaitingPeriodPublicationStatus.PUBLISHED
    assert publication.source_candidate_ids == (
        "candidate_page_31",
        "candidate_page_32",
        "candidate_page_44",
    )


def test_ped_base_waiting_period_is_36_months() -> None:
    ped = _by_type(WaitingPeriodType.PRE_EXISTING_DISEASE)
    assert ped.duration_value == 36
    assert ped.duration_unit is WaitingPeriodDurationUnit.MONTHS
    assert ped.start_basis is WaitingPeriodStartBasis.INSURED_PERSON_FIRST_COVERAGE
    assert "treatment of a pre-existing disease" in ped.applies_to
    assert "direct complications of a pre-existing disease" in ped.applies_to


def test_ped_portability_credit_is_preserved_as_modification() -> None:
    ped = _by_type(WaitingPeriodType.PRE_EXISTING_DISEASE)
    assert len(ped.modifications) == 1
    modification = ped.modifications[0]
    assert modification.modification_type is WaitingPeriodModificationType.CREDIT_FOR_CONTINUITY
    assert modification.resulting_duration_value == 36
    assert modification.resulting_duration_unit is WaitingPeriodDurationUnit.MONTHS


def test_specific_disease_base_waiting_period_is_24_months() -> None:
    item = _by_type(WaitingPeriodType.SPECIFIC_DISEASE_PROCEDURE)
    assert item.duration_value == 24
    assert item.duration_unit is WaitingPeriodDurationUnit.MONTHS
    assert item.start_basis is WaitingPeriodStartBasis.INSURED_PERSON_FIRST_COVERAGE
    assert item.exclusions_or_exceptions == ("claims arising due to an accident",)


def test_initial_waiting_period_is_30_days_with_reviewed_exceptions() -> None:
    item = _by_type(WaitingPeriodType.INITIAL)
    assert item.duration_value == 30
    assert item.duration_unit is WaitingPeriodDurationUnit.DAYS
    assert item.start_basis is WaitingPeriodStartBasis.POLICY_INCEPTION
    assert item.exclusions_or_exceptions == (
        "covered claims arising due to an accident",
        "the exclusion does not apply where the insured person has Continuous Coverage for more than twelve months",
    )


def test_optional_buy_back_is_not_part_of_base_publication() -> None:
    publication_text = repr(STAR_COMPREHENSIVE_WAITING_PERIOD_PUBLICATION)
    assert "12 months" not in publication_text
    assert any("Optional Buy Back" in item for item in STAR_COMPREHENSIVE_WAITING_PERIOD_PUBLICATION.limitations)


def test_publication_does_not_promote_registry_yet() -> None:
    waiting = next(item for item in STAR_COMPREHENSIVE_COVERAGE.concepts if item.concept_id == "waiting_periods")
    assert waiting.status.value == "NOT_AUTOMATED"
    assert waiting.comparison_ready is False
    assert waiting.decision_support_ready is False


def test_publication_keeps_material_interaction_and_enhancement_limitations() -> None:
    limitations = STAR_COMPREHENSIVE_WAITING_PERIOD_PUBLICATION.limitations
    assert any("longer applicable waiting period" in item for item in limitations)
    assert any("enhanced Sum Insured" in item for item in limitations)


def test_publication_has_exact_three_base_mechanics() -> None:
    assert tuple(item.waiting_period_type for item in STAR_COMPREHENSIVE_WAITING_PERIOD_PUBLICATION.mechanics) == (
        WaitingPeriodType.PRE_EXISTING_DISEASE,
        WaitingPeriodType.SPECIFIC_DISEASE_PROCEDURE,
        WaitingPeriodType.INITIAL,
    )
