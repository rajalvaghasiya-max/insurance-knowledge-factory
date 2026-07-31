"""Governed benefit catalogue entries for MO-025C."""
from __future__ import annotations

from datetime import date

from insurance_intelligence.benefits.contracts import (
    BenefitConcept,
    PublicationStatus,
    ReviewStatus,
)

RESTORATION_CONCEPT_ID = "health:coverage_capacity:restoration_benefit"

RESTORATION_BENEFIT_CONCEPT = BenefitConcept(
    concept_id=RESTORATION_CONCEPT_ID,
    canonical_name="Restoration of Sum Insured",
    definition=(
        "A product benefit that replenishes all or part of the available sum insured "
        "after a governed trigger, subject to product-specific conditions and limits."
    ),
    benefit_family="sum_insured_behavior",
    allowed_mechanic_dimensions=(
        "restoration_percentage",
        "restoration_count_per_policy_period",
        "trigger_requirement",
        "trigger_timing",
        "same_hospitalization_use",
        "subsequent_hospitalization_use",
        "same_illness_use",
        "covered_section_scope",
        "relapse_window_days",
        "policy_year_reset",
        "carry_over_between_policy_years",
        "floater_operation",
    ),
    review_status=ReviewStatus.APPROVED,
    publication_status=PublicationStatus.PUBLISHED,
    effective_from=date(2025, 1, 1),
)

__all__ = [
    "RESTORATION_BENEFIT_CONCEPT",
    "RESTORATION_CONCEPT_ID",
]
