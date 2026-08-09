"""Initial governed restoration assessment policy for MO-026B.

This policy assesses restoration mechanics only on their intrinsic product terms.
It does not account for customer-specific priorities or convert the result into an
overall product ranking or recommendation.
"""
from __future__ import annotations

from datetime import date

from insurance_intelligence.benefits.assessment_contracts import AssessmentBand
from insurance_intelligence.benefits.assessment_policies import (
    AssessmentBandRule,
    AssessmentCriterion,
    BenefitAssessmentPolicy,
    CriterionOperator,
)
from insurance_intelligence.benefits.contracts import PublicationStatus, ReviewStatus


RESTORATION_ASSESSMENT_POLICY = BenefitAssessmentPolicy(
    policy_id="assessment_policy:health:restoration:v1",
    policy_version="1.0",
    dimension_id="restoration",
    required_mechanic_ids=(
        "restoration_percentage",
        "restoration_count_per_policy_period",
        "trigger_requirement",
        "same_hospitalization_use",
        "subsequent_hospitalization_use",
    ),
    band_rules=(
        AssessmentBandRule(
            rule_id="restoration:very_strong",
            band=AssessmentBand.VERY_STRONG,
            criteria=(
                AssessmentCriterion(
                    mechanic_id="restoration_percentage",
                    operator=CriterionOperator.EQUALS,
                    expected_value=100,
                    rationale="A full restoration preserves the governed base amount per activation.",
                ),
                AssessmentCriterion(
                    mechanic_id="restoration_count_per_policy_period",
                    operator=CriterionOperator.EQUALS,
                    expected_value="unlimited_during_policy_year",
                    rationale="Unlimited activations are intrinsically more flexible than a finite count.",
                ),
                AssessmentCriterion(
                    mechanic_id="same_hospitalization_use",
                    operator=CriterionOperator.EQUALS,
                    expected_value=True,
                    rationale="Same-hospitalization use improves restoration availability when governed conditions are met.",
                ),
                AssessmentCriterion(
                    mechanic_id="subsequent_hospitalization_use",
                    operator=CriterionOperator.EQUALS,
                    expected_value=True,
                    rationale="Subsequent-hospitalization use preserves utility across later admissible claims.",
                ),
            ),
            explanation_template=(
                "Restoration mechanics are very strong on their own terms because the governed implementation "
                "restores the full base amount, supports unlimited activations, and permits use in both same and "
                "subsequent hospitalizations subject to the product trigger and scope."
            ),
        ),
        AssessmentBandRule(
            rule_id="restoration:strong",
            band=AssessmentBand.STRONG,
            criteria=(
                AssessmentCriterion(
                    mechanic_id="restoration_percentage",
                    operator=CriterionOperator.EQUALS,
                    expected_value=100,
                    rationale="A full restoration is materially useful when the governed trigger is reached.",
                ),
                AssessmentCriterion(
                    mechanic_id="subsequent_hospitalization_use",
                    operator=CriterionOperator.EQUALS,
                    expected_value=True,
                    rationale="Use for subsequent hospitalization preserves meaningful replenishment value.",
                ),
            ),
            explanation_template=(
                "Restoration mechanics are strong on their own terms because the governed implementation restores "
                "the full base amount and supports subsequent-hospitalization use, while frequency, same-claim use, "
                "trigger, and scope remain important qualifiers."
            ),
        ),
        AssessmentBandRule(
            rule_id="restoration:moderate",
            band=AssessmentBand.MODERATE,
            criteria=(
                AssessmentCriterion(
                    mechanic_id="restoration_percentage",
                    operator=CriterionOperator.PRESENT,
                    rationale="A governed restoration amount exists but stronger mechanic conditions are not established.",
                ),
                AssessmentCriterion(
                    mechanic_id="trigger_requirement",
                    operator=CriterionOperator.PRESENT,
                    rationale="The trigger is explicitly governed and must remain visible in the assessment.",
                ),
            ),
            explanation_template=(
                "Restoration is available, but the governed mechanics do not satisfy the stronger policy bands. "
                "The amount, frequency, trigger, same-claim use, and scope should be read together."
            ),
        ),
    ),
    not_scorable_reason=(
        "Restoration cannot be assessed when one or more required governed mechanics are missing or unresolved."
    ),
    governance_basis=(
        "PolicyScna education-first qualitative policy choice. Bands describe intrinsic restoration flexibility "
        "only and must not be interpreted as an overall product score or customer suitability judgment."
    ),
    review_status=ReviewStatus.APPROVED,
    publication_status=PublicationStatus.PUBLISHED,
    effective_from=date(2026, 8, 9),
)


__all__ = ["RESTORATION_ASSESSMENT_POLICY"]
