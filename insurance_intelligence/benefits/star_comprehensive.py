"""Governed Star Comprehensive restoration implementation for MO-025C."""
from __future__ import annotations

from datetime import date

from insurance_intelligence.benefits.catalogue import (
    RESTORATION_BENEFIT_CONCEPT,
    RESTORATION_CONCEPT_ID,
)
from insurance_intelligence.benefits.contracts import (
    BenefitAvailability,
    BenefitEvidenceReference,
    BenefitImplementationType,
    BenefitMechanic,
    MechanicValueType,
    ProductBenefitImplementation,
    PublicationStatus,
    ReviewStatus,
)

STAR_COMPREHENSIVE_PRODUCT_VARIANT_ID = "pv_star_health_star_comprehensive_shahlip26044v092526"

_POLICY_EVIDENCE_ID = "ev_star_comprehensive_restoration_policy_wording"
_PROSPECTUS_EVIDENCE_ID = "ev_star_comprehensive_restoration_prospectus"

STAR_COMPREHENSIVE_RESTORATION_EVIDENCE = (
    BenefitEvidenceReference(
        evidence_reference_id=_POLICY_EVIDENCE_ID,
        source_document_id="star_health_star_comprehensive_policy_wording_shahlip26044v092526",
        source_sha256="b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f",
        authority_type="policy_wording",
        evidence_locator="Section II.13, policy wording page 12 of 47; Important Note 28(i)-(ii), page 44 of 47",
        bounded_evidence_identity="bounded:star_comprehensive:restoration:policy_wording:v24_2025",
    ),
    BenefitEvidenceReference(
        evidence_reference_id=_PROSPECTUS_EVIDENCE_ID,
        source_document_id="star_health_star_comprehensive_prospectus_shahlip26044v092526",
        source_sha256="0404693147bd5202e28e39bfdb8fcc87f78e7ee6aa6a6f1032f63cbec63698e1",
        authority_type="prospectus",
        evidence_locator="Section 13, prospectus pages 7-8 of 52",
        bounded_evidence_identity="bounded:star_comprehensive:restoration:prospectus:v15_2025",
    ),
)

_ALL_EVIDENCE_IDS = (_POLICY_EVIDENCE_ID, _PROSPECTUS_EVIDENCE_ID)

STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION = ProductBenefitImplementation(
    implementation_id="benefit_impl:star_health:star_comprehensive:automatic_restoration:v1",
    concept_id=RESTORATION_CONCEPT_ID,
    insurer_id="star_health",
    product_id="star_comprehensive",
    product_variant_id=STAR_COMPREHENSIVE_PRODUCT_VARIANT_ID,
    marketing_name="Automatic Restoration of Sum Insured",
    availability=BenefitAvailability.INCLUDED,
    implementation_type=BenefitImplementationType.BUILT_IN,
    mechanics=(
        BenefitMechanic(
            dimension_id="restoration_percentage",
            value_type=MechanicValueType.PERCENTAGE,
            value=100,
            unit="percent_of_basic_sum_insured",
            evidence_reference_ids=_ALL_EVIDENCE_IDS,
        ),
        BenefitMechanic(
            dimension_id="restoration_count_per_policy_period",
            value_type=MechanicValueType.INTEGER,
            value=1,
            evidence_reference_ids=_ALL_EVIDENCE_IDS,
        ),
        BenefitMechanic(
            dimension_id="trigger_requirement",
            value_type=MechanicValueType.ENUM,
            value="exhaustion_of_basic_sum_insured_and_accrued_cumulative_bonus_if_any",
            evidence_reference_ids=_ALL_EVIDENCE_IDS,
        ),
        BenefitMechanic(
            dimension_id="trigger_timing",
            value_type=MechanicValueType.ENUM,
            value="immediately_upon_exhaustion",
            evidence_reference_ids=_ALL_EVIDENCE_IDS,
        ),
        BenefitMechanic(
            dimension_id="same_hospitalization_use",
            value_type=MechanicValueType.BOOLEAN,
            value=False,
            evidence_reference_ids=_ALL_EVIDENCE_IDS,
        ),
        BenefitMechanic(
            dimension_id="subsequent_hospitalization_use",
            value_type=MechanicValueType.BOOLEAN,
            value=True,
            evidence_reference_ids=_ALL_EVIDENCE_IDS,
        ),
        BenefitMechanic(
            dimension_id="same_illness_use",
            value_type=MechanicValueType.BOOLEAN,
            value=True,
            evidence_reference_ids=_ALL_EVIDENCE_IDS,
        ),
        BenefitMechanic(
            dimension_id="covered_section_scope",
            value_type=MechanicValueType.TEXT,
            value="II.1, II.3, II.5, II.6, II.7, II.8 and II.11",
            evidence_reference_ids=_ALL_EVIDENCE_IDS,
        ),
        BenefitMechanic(
            dimension_id="relapse_window_days",
            value_type=MechanicValueType.INTEGER,
            value=45,
            applicability={"meaning": "relapse within this period is treated as the same hospitalization"},
            evidence_reference_ids=_ALL_EVIDENCE_IDS,
        ),
        BenefitMechanic(
            dimension_id="policy_year_reset",
            value_type=MechanicValueType.BOOLEAN,
            value=True,
            evidence_reference_ids=(_POLICY_EVIDENCE_ID,),
        ),
        BenefitMechanic(
            dimension_id="carry_over_between_policy_years",
            value_type=MechanicValueType.BOOLEAN,
            value=False,
            evidence_reference_ids=(_POLICY_EVIDENCE_ID,),
        ),
        BenefitMechanic(
            dimension_id="floater_operation",
            value_type=MechanicValueType.ENUM,
            value="floats_among_insured_persons",
            evidence_reference_ids=(_POLICY_EVIDENCE_ID,),
        ),
    ),
    evidence_references=STAR_COMPREHENSIVE_RESTORATION_EVIDENCE,
    behaviour_signature_id="bsig:star_comprehensive:restoration:100pct_once_after_full_exhaustion_subsequent_hospitalization",
    conditions=(
        "Restoration activates only after exhaustion of the Basic Sum Insured and accrued Cumulative Bonus, if any.",
        "The restored amount is available only for a subsequent hospitalization.",
        "The restored amount is available only for claims under Sections II.1, II.3, II.5, II.6, II.7, II.8 and II.11.",
        "Claims remain subject to the policy definition of Any One Illness.",
    ),
    limitations=(
        "Restoration is available once during each Policy Period.",
        "A relapse within 45 days from the last hospital consultation is treated as the same hospitalization.",
        "Benefits for later years of a multi-year policy cannot be brought forward into an earlier year.",
        "The restoration benefit does not carry over between policy years.",
    ),
    exclusions=(
        "Use within the same hospitalization is not supported by the governing clause.",
        "Claims outside the listed coverage sections are outside this restoration implementation.",
    ),
    review_status=ReviewStatus.APPROVED,
    publication_status=PublicationStatus.PUBLISHED,
    effective_from=date(2025, 1, 1),
)

STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.validate_against(RESTORATION_BENEFIT_CONCEPT)

__all__ = [
    "STAR_COMPREHENSIVE_PRODUCT_VARIANT_ID",
    "STAR_COMPREHENSIVE_RESTORATION_EVIDENCE",
    "STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION",
]
