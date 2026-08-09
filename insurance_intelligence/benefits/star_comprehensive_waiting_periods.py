"""Governed Star Comprehensive base waiting-period publication for MO-028B.5.

This module projects only the human-approved base exclusion mechanics recorded in
STAR_COMPREHENSIVE_WAITING_PERIOD_REVIEW_DECISION.json. Optional Buy Back wording
is intentionally excluded from the base publication. Registry promotion is a
separate step.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.benefits.waiting_period_contracts import (
    WaitingPeriodDurationUnit,
    WaitingPeriodMechanic,
    WaitingPeriodModification,
    WaitingPeriodModificationType,
    WaitingPeriodStartBasis,
    WaitingPeriodType,
)


class WaitingPeriodPublicationReviewStatus(str, Enum):
    APPROVED = "APPROVED"


class WaitingPeriodPublicationStatus(str, Enum):
    PUBLISHED = "PUBLISHED"


@dataclass(frozen=True)
class GovernedWaitingPeriodPublication:
    publication_id: str
    insurer_id: str
    product_id: str
    product_variant_id: str
    product_uin: str
    mechanics: tuple[WaitingPeriodMechanic, ...]
    source_document_id: str
    source_document_version_id: str
    source_document_sha256: str
    source_candidate_ids: tuple[str, ...]
    review_status: WaitingPeriodPublicationReviewStatus
    publication_status: WaitingPeriodPublicationStatus
    limitations: tuple[str, ...]


STAR_COMPREHENSIVE_WAITING_PERIOD_PUBLICATION = GovernedWaitingPeriodPublication(
    publication_id="waiting_period_fact:star_health:star_comprehensive:base:v1",
    insurer_id="star_health",
    product_id="star_comprehensive",
    product_variant_id="pv_star_health_star_comprehensive_shahlip26044v092526",
    product_uin="SHAHLIP26044V092526",
    mechanics=(
        WaitingPeriodMechanic(
            waiting_period_type=WaitingPeriodType.PRE_EXISTING_DISEASE,
            duration_value=36,
            duration_unit=WaitingPeriodDurationUnit.MONTHS,
            start_basis=WaitingPeriodStartBasis.INSURED_PERSON_FIRST_COVERAGE,
            applies_to=(
                "treatment of a pre-existing disease",
                "direct complications of a pre-existing disease",
            ),
            evidence_reference_ids=(
                "star_waiting_period:candidate_page_31:ped_base",
                "star_waiting_period:candidate_page_44:sum_insured_enhancement_support",
            ),
            modifications=(
                WaitingPeriodModification(
                    modification_type=WaitingPeriodModificationType.CREDIT_FOR_CONTINUITY,
                    condition=(
                        "Continuous coverage without a break under applicable portability norms may reduce the remaining waiting period to the extent of prior coverage."
                    ),
                    resulting_duration_value=36,
                    resulting_duration_unit=WaitingPeriodDurationUnit.MONTHS,
                    evidence_reference_ids=(
                        "star_waiting_period:candidate_page_31:ped_portability_credit",
                    ),
                ),
            ),
            continuity_dependency=(
                "36 months of continuous coverage after inception of the first policy with insurer; portability continuity may reduce the remaining waiting period to the extent of prior coverage"
            ),
        ),
        WaitingPeriodMechanic(
            waiting_period_type=WaitingPeriodType.SPECIFIC_DISEASE_PROCEDURE,
            duration_value=24,
            duration_unit=WaitingPeriodDurationUnit.MONTHS,
            start_basis=WaitingPeriodStartBasis.INSURED_PERSON_FIRST_COVERAGE,
            applies_to=(
                "listed specified diseases",
                "listed specified procedures and treatments",
            ),
            evidence_reference_ids=(
                "star_waiting_period:candidate_page_31:specified_base",
                "star_waiting_period:candidate_page_32:specified_list_continuation",
                "star_waiting_period:candidate_page_44:sum_insured_enhancement_support",
            ),
            exclusions_or_exceptions=(
                "claims arising due to an accident",
            ),
            modifications=(
                WaitingPeriodModification(
                    modification_type=WaitingPeriodModificationType.CREDIT_FOR_CONTINUITY,
                    condition=(
                        "Continuous prior coverage under applicable portability norms may reduce the waiting period to the extent of prior coverage."
                    ),
                    resulting_duration_value=24,
                    resulting_duration_unit=WaitingPeriodDurationUnit.MONTHS,
                    evidence_reference_ids=(
                        "star_waiting_period:candidate_page_32:specified_portability_credit",
                    ),
                ),
            ),
            continuity_dependency=(
                "24 months of continuous coverage after inception of the first policy with Star Health; portability continuity may reduce the waiting period to the extent of prior coverage"
            ),
        ),
        WaitingPeriodMechanic(
            waiting_period_type=WaitingPeriodType.INITIAL,
            duration_value=30,
            duration_unit=WaitingPeriodDurationUnit.DAYS,
            start_basis=WaitingPeriodStartBasis.POLICY_INCEPTION,
            applies_to=(
                "treatment of any illness within 30 days from the first policy commencement date",
            ),
            evidence_reference_ids=(
                "star_waiting_period:candidate_page_32:initial_base",
                "star_waiting_period:candidate_page_44:sum_insured_enhancement_support",
            ),
            exclusions_or_exceptions=(
                "covered claims arising due to an accident",
                "the exclusion does not apply where the insured person has Continuous Coverage for more than twelve months",
            ),
        ),
    ),
    source_document_id="star_health_star_comprehensive_policy_wording_v1",
    source_document_version_id="docver_star_health_star_comprehensive_policy_wording_v1_b1dbe8fb78646f75",
    source_document_sha256="b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f",
    source_candidate_ids=("candidate_page_31", "candidate_page_32", "candidate_page_44"),
    review_status=WaitingPeriodPublicationReviewStatus.APPROVED,
    publication_status=WaitingPeriodPublicationStatus.PUBLISHED,
    limitations=(
        "This publication covers only the reviewed base waiting-period exclusions.",
        "Optional Buy Back wording that reduces the PED waiting period to 12 months is not part of this base publication.",
        "A waiting-period mechanic does not determine claim admissibility or payment for a specific claim.",
        "Coverage after a PED waiting period remains subject to declaration and insurer acceptance as recorded in the reviewed base clause.",
        "Where a specified disease/procedure is also subject to the PED waiting period, the longer applicable waiting period governs.",
        "Waiting periods reapply to the extent of an enhanced Sum Insured as recorded in the reviewed policy wording.",
    ),
)


__all__ = [
    "GovernedWaitingPeriodPublication",
    "STAR_COMPREHENSIVE_WAITING_PERIOD_PUBLICATION",
    "WaitingPeriodPublicationReviewStatus",
    "WaitingPeriodPublicationStatus",
]
