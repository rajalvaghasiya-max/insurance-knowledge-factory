"""Initial governed restoration assessment policy for MO-026B.

This policy assesses restoration mechanics only on their intrinsic product terms.
Version 1 intentionally recognizes only mechanic combinations already certified by
the governed Star Comprehensive and Activ One NXT restoration pilots. Unknown or
materially different combinations fail closed as NOT_SCORABLE rather than being
forced into a qualitative band.

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
            rule_id="restoration:very_strong:certified_unlimited_same_hospitalization",
            band=AssessmentBand.VERY_STRONG,
            criteria=(
                AssessmentCriterion(
                    mechanic_id="restoration_percentage",
                    operator=CriterionOperator.EQUALS,
                    expected_value=100,
                    rationale="The certified implementation restores the full governed base amount per activation.",
                ),
                AssessmentCriterion(
                    mechanic_id="restoration_count_per_policy_period",
                    operator=CriterionOperator.EQUALS,
                    expected_value="unlimited_during_policy_year",
                    rationale="The certified implementation supports unlimited activations during the policy year.",
                ),
                AssessmentCriterion(
                    mechanic_id="trigger_requirement",
                    operator=CriterionOperator.PRESENT,
                    rationale="The restoration trigger must remain explicitly governed.",
                ),
                AssessmentCriterion(
                    mechanic_id="same_hospitalization_use",
                    operator=CriterionOperator.EQUALS,
                    expected_value=True,
                    rationale="The certified implementation supports same-hospitalization use when governed conditions are met.",
                ),
                AssessmentCriterion(
                    mechanic_id="subsequent_hospitalization_use",
                    operator=CriterionOperator.EQUALS,
                    expected_value=True,
                    rationale="The certified implementation also supports subsequent-hospitalization use.",
                ),
            ),
            explanation_template=(
                "Restoration mechanics are very strong on their own terms because the governed implementation "
                "restores the full base amount, supports unlimited activations, and permits use in both same and "
                "subsequent hospitalizations subject to the governed trigger and scope."
            ),
        ),
        AssessmentBandRule(
            rule_id="restoration:strong:certified_once_subsequent_hospitalization",
            band=AssessmentBand.STRONG,
            criteria=(
                AssessmentCriterion(
                    mechanic_id="restoration_percentage",
                    operator=CriterionOperator.EQUALS,
                    expected_value=100,
                    rationale="The certified implementation restores the full governed base amount when its trigger is reached.",
                ),
                AssessmentCriterion(
                    mechanic_id="restoration_count_per_policy_period",
                    operator=CriterionOperator.EQUALS,
                    expected_value=1,
                    rationale="The certified implementation permits one restoration during each policy period.",
                ),
                AssessmentCriterion(
                    mechanic_id="trigger_requirement",
                    operator=CriterionOperator.PRESENT,
                    rationale="The restoration trigger must remain explicitly governed.",
                ),
                AssessmentCriterion(
                    mechanic_id="same_hospitalization_use",
                    operator=CriterionOperator.EQUALS,
                    expected_value=False,
                    rationale="The certified implementation does not support use within the same hospitalization.",
                ),
                AssessmentCriterion(
                    mechanic_id="subsequent_hospitalization_use",
                    operator=CriterionOperator.EQUALS,
                    expected_value=True,
                    rationale="The certified implementation supports use for a subsequent hospitalization.",
                ),
            ),
            explanation_template=(
                "Restoration mechanics are strong on their own terms because the governed implementation restores "
                "the full base amount for one activation and supports subsequent-hospitalization use; same-hospitalization "
                "use is not supported and the trigger and scope remain important qualifiers."
            ),
        ),
    ),
    not_scorable_reason=(
        "Restoration cannot be assessed when required governed mechanics are missing, unresolved, or outside a certified assessment signature."
    ),
    governance_basis=(
        "PolicyScna education-first qualitative policy choice. Version 1 recognizes only restoration mechanic signatures "
        "already certified by the governed Star Comprehensive and Activ One NXT pilots. Bands describe intrinsic restoration "
        "flexibility only and must not be interpreted as an overall product score or customer suitability judgment."
    ),
    review_status=ReviewStatus.APPROVED,
    publication_status=PublicationStatus.PUBLISHED,
    effective_from=date(2026, 8, 9),
)


__all__ = ["RESTORATION_ASSESSMENT_POLICY"]
