"""Guarded AR-2.4 projection -> MO-026 assessment bridge.

This module connects the newer Generic Knowledge comparison projection to the existing
education-first assessment/comparison stack without teaching MO-026 about waiting-period or
benefit-limit ontologies.

A comparable projection may carry forward an already-governed assessed BenefitAssessment.
A blocked projection always becomes NOT_SCORABLE, and an explicit non-applicability projection
always becomes NOT_APPLICABLE.  A caller therefore cannot attach a favorable qualitative band
to a semantic dimension that the producer marked not comparable.
"""
from __future__ import annotations

from hashlib import sha256

from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentStatus,
    BenefitAssessment,
    DecisionRole,
)
from insurance_intelligence.generic_knowledge.comparison_projection import (
    ComparableDimension,
    ComparisonDimensionProjection,
    NotApplicableDimension,
    NotComparableDimension,
)


class ComparisonProjectionAssessmentBridgeError(ValueError):
    """Raised when a projection cannot be carried safely into MO-026 assessment."""


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ComparisonProjectionAssessmentBridgeError(
            f"{field_name} must be non-empty text"
        )
    return value.strip()


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ComparisonProjectionAssessmentBridgeError(f"{field_name} must be a tuple")
    cleaned = tuple(_text(value, field_name) for value in values)
    if not cleaned:
        raise ComparisonProjectionAssessmentBridgeError(f"{field_name} must not be empty")
    if len(cleaned) != len(set(cleaned)):
        raise ComparisonProjectionAssessmentBridgeError(
            f"{field_name} must not contain duplicates"
        )
    return cleaned


def _bridge_assessment_id(
    *, projection: ComparisonDimensionProjection, implementation_id: str, status: AssessmentStatus
) -> str:
    payload = "\x1f".join(
        (
            projection.source_family,
            projection.concept_id,
            projection.dimension_id,
            implementation_id,
            status.value,
        )
    )
    return f"projection-assessment-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _validate_assessed_passthrough(
    projection: ComparableDimension,
    assessment: BenefitAssessment,
    *,
    implementation_id: str,
    decision_role: DecisionRole,
) -> BenefitAssessment:
    if type(assessment) is not BenefitAssessment:
        raise ComparisonProjectionAssessmentBridgeError(
            "ComparableDimension requires an exact BenefitAssessment passthrough"
        )
    if not assessment.is_assessed:
        raise ComparisonProjectionAssessmentBridgeError(
            "ComparableDimension passthrough must already be assessed"
        )
    if assessment.concept_id != projection.concept_id:
        raise ComparisonProjectionAssessmentBridgeError(
            "assessment concept_id must match comparable projection"
        )
    if assessment.dimension_id != projection.dimension_id:
        raise ComparisonProjectionAssessmentBridgeError(
            "assessment dimension_id must match comparable projection"
        )
    if assessment.implementation_id != implementation_id:
        raise ComparisonProjectionAssessmentBridgeError(
            "assessment implementation_id must match bridge implementation_id"
        )
    if assessment.decision_role is not decision_role:
        raise ComparisonProjectionAssessmentBridgeError(
            "assessment decision_role must match bridge decision_role"
        )
    missing_evidence = tuple(
        evidence_id
        for evidence_id in projection.evidence_ids
        if evidence_id not in assessment.evidence_reference_ids
    )
    if missing_evidence:
        raise ComparisonProjectionAssessmentBridgeError(
            "assessed passthrough must preserve all projection evidence ids"
        )
    return assessment


def assessment_from_comparison_projection(
    *,
    projection: ComparisonDimensionProjection,
    implementation_id: str,
    decision_role: DecisionRole,
    source_mechanic_ids: tuple[str, ...],
    comparable_assessment: BenefitAssessment | None = None,
) -> BenefitAssessment:
    """Translate one projection into the existing assessment contract, fail closed.

    ``source_mechanic_ids`` carries the producer-side fact/mechanic identifiers used to create
    the projection.  It is lineage only; it does not influence readiness.
    """

    implementation_id = _text(implementation_id, "implementation_id")
    if not isinstance(decision_role, DecisionRole):
        raise ComparisonProjectionAssessmentBridgeError(
            "decision_role must be a DecisionRole"
        )
    source_mechanic_ids = _text_tuple(source_mechanic_ids, "source_mechanic_ids")

    if isinstance(projection, ComparableDimension):
        if comparable_assessment is None:
            raise ComparisonProjectionAssessmentBridgeError(
                "ComparableDimension requires a governed comparable_assessment"
            )
        return _validate_assessed_passthrough(
            projection,
            comparable_assessment,
            implementation_id=implementation_id,
            decision_role=decision_role,
        )

    if comparable_assessment is not None:
        raise ComparisonProjectionAssessmentBridgeError(
            "blocked/non-applicable projections cannot carry an assessed passthrough"
        )

    if isinstance(projection, NotComparableDimension):
        limitations = tuple(dict.fromkeys(projection.blocking_reasons))
        return BenefitAssessment(
            assessment_id=_bridge_assessment_id(
                projection=projection,
                implementation_id=implementation_id,
                status=AssessmentStatus.NOT_SCORABLE,
            ),
            implementation_id=implementation_id,
            concept_id=projection.concept_id,
            dimension_id=projection.dimension_id,
            decision_role=decision_role,
            status=AssessmentStatus.NOT_SCORABLE,
            assessment_band=None,
            assessment_policy_id=None,
            assessment_policy_version=None,
            summary="Assessment unavailable because certified product knowledge is not comparison-ready.",
            practical_meaning=(
                "PolicyScna preserves this dimension as unresolved and will not turn incomplete "
                "product knowledge into a favorable or unfavorable assessment."
            ),
            source_mechanic_ids=source_mechanic_ids,
            evidence_reference_ids=projection.evidence_ids,
            limitations=limitations,
        )

    if isinstance(projection, NotApplicableDimension):
        return BenefitAssessment(
            assessment_id=_bridge_assessment_id(
                projection=projection,
                implementation_id=implementation_id,
                status=AssessmentStatus.NOT_APPLICABLE,
            ),
            implementation_id=implementation_id,
            concept_id=projection.concept_id,
            dimension_id=projection.dimension_id,
            decision_role=decision_role,
            status=AssessmentStatus.NOT_APPLICABLE,
            assessment_band=None,
            assessment_policy_id=None,
            assessment_policy_version=None,
            summary="This governed dimension is explicitly not applicable.",
            practical_meaning=projection.reason,
            source_mechanic_ids=source_mechanic_ids,
            evidence_reference_ids=projection.evidence_ids,
            limitations=(),
        )

    raise ComparisonProjectionAssessmentBridgeError(
        "projection must be a supported ComparisonDimensionProjection variant"
    )


__all__ = [
    "ComparisonProjectionAssessmentBridgeError",
    "assessment_from_comparison_projection",
]
