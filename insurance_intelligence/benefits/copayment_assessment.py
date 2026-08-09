"""Protection-floor copayment assessment for MO-026C.

Copayment is assessed from the governed condition projection, not from a duplicate
product-benefit catalogue record. The output remains education-first and never
produces a product rank, winner, suitability conclusion, or recommendation.
"""
from __future__ import annotations

from hashlib import sha256

from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentBand,
    AssessmentStatus,
    BenefitAssessment,
    DecisionRole,
)
from insurance_intelligence.benefits.condition_assessment_projection import (
    GovernedConditionAssessmentProjection,
)


COPAYMENT_ASSESSMENT_POLICY_ID = "assessment_policy:health:copayment:v1"
COPAYMENT_ASSESSMENT_POLICY_VERSION = "1.0"


class CopaymentAssessmentError(ValueError):
    """Raised when governed copayment mechanics are incompatible with assessment."""


def _assessment_id(projection: GovernedConditionAssessmentProjection) -> str:
    payload = "\x1f".join(
        (
            projection.finding_id,
            COPAYMENT_ASSESSMENT_POLICY_ID,
            COPAYMENT_ASSESSMENT_POLICY_VERSION,
        )
    )
    return f"assessment-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _band_for_percentage(percentage: float) -> AssessmentBand:
    """Governed v1 intrinsic severity bands for an applicable copayment percentage."""

    if percentage == 0:
        return AssessmentBand.VERY_STRONG
    if percentage <= 10:
        return AssessmentBand.MODERATE
    if percentage <= 20:
        return AssessmentBand.RESTRICTIVE
    return AssessmentBand.VERY_RESTRICTIVE


def assess_conditional_copayment(
    projection: GovernedConditionAssessmentProjection,
) -> BenefitAssessment:
    """Assess one evidence-backed conditional copayment as a protection floor."""

    if type(projection) is not GovernedConditionAssessmentProjection:
        raise CopaymentAssessmentError(
            "projection must be the exact GovernedConditionAssessmentProjection type"
        )
    if projection.dimension_id != "copayment":
        raise CopaymentAssessmentError("projection dimension_id must be copayment")

    missing_semantics: list[str] = []
    if not projection.trigger.strip():
        missing_semantics.append("trigger")
    # Conditional copayment can legitimately have no exception or no explicit section scope,
    # but those absences must remain visible as limitations rather than be inferred away.
    limitations: list[str] = []
    if projection.exception is None:
        limitations.append("No governed exception clause is available for this copayment condition.")
    if projection.applicability_scope is None:
        limitations.append("No narrower governed applicability scope is available for this copayment condition.")
    if missing_semantics:
        return BenefitAssessment(
            assessment_id=_assessment_id(projection),
            implementation_id=f"reasoning_finding:{projection.finding_id}",
            concept_id="health:cost_sharing:copayment",
            dimension_id="copayment",
            decision_role=DecisionRole.PROTECTION_FLOOR,
            status=AssessmentStatus.NOT_SCORABLE,
            assessment_band=None,
            assessment_policy_id=COPAYMENT_ASSESSMENT_POLICY_ID,
            assessment_policy_version=COPAYMENT_ASSESSMENT_POLICY_VERSION,
            summary="Copayment assessment is unavailable because required conditional semantics are unresolved.",
            practical_meaning="PolicyScna will not classify a copayment whose trigger is not governed.",
            source_mechanic_ids=("copayment_percentage", "copayment_trigger"),
            evidence_reference_ids=projection.evidence_ids,
            limitations=tuple(
                [f"Missing required copayment semantics: {', '.join(missing_semantics)}."]
                + limitations
            ),
        )

    band = _band_for_percentage(projection.percentage)
    qualifier = "conditional"
    if projection.exception is not None:
        qualifier += " with a governed exception"
    if projection.applicability_scope is not None:
        qualifier += " and governed scope"

    limitations.append(
        "This is an intrinsic assessment of the documented copayment restriction only; actual applicability depends on the governed trigger, exception, and scope."
    )
    return BenefitAssessment(
        assessment_id=_assessment_id(projection),
        implementation_id=f"reasoning_finding:{projection.finding_id}",
        concept_id="health:cost_sharing:copayment",
        dimension_id="copayment",
        decision_role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.ASSESSED_WITH_LIMITATIONS,
        assessment_band=band,
        assessment_policy_id=COPAYMENT_ASSESSMENT_POLICY_ID,
        assessment_policy_version=COPAYMENT_ASSESSMENT_POLICY_VERSION,
        summary=(
            f"The policy contains a {projection.percentage:g}% {qualifier} copayment. "
            "The percentage must be read together with its trigger, exception, and applicability scope."
        ),
        practical_meaning=(
            "When the governed condition applies, the insured bears the documented percentage of the admissible claim amount. "
            "This material protection restriction remains visible regardless of later user preference weighting."
        ),
        source_mechanic_ids=(
            "copayment_percentage",
            "copayment_trigger",
            "copayment_exception",
            "copayment_scope",
        ),
        evidence_reference_ids=projection.evidence_ids,
        limitations=tuple(limitations),
    )


__all__ = [
    "COPAYMENT_ASSESSMENT_POLICY_ID",
    "COPAYMENT_ASSESSMENT_POLICY_VERSION",
    "CopaymentAssessmentError",
    "assess_conditional_copayment",
]
