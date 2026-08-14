"""Fail-closed waiting-period adapter into the AR-2.4 comparison projection.

The adapter translates governed waiting-period accounting + semantic resolution into the
ontology-neutral comparison boundary.  It does not compare products or assign qualitative
bands.  A comparable value is emitted only when the normative unit is mapped, semantic
resolution is RESOLVED, and no material residue/publication blocker remains.
"""
from __future__ import annotations

from typing import Any, Mapping

from insurance_intelligence.generic_knowledge.comparison_projection import (
    ComparableDimension,
    ComparisonDimensionProjection,
    NotApplicableDimension,
    NotApplicableReasonCode,
    NotComparableDimension,
    NotComparableReasonCode,
)
from insurance_intelligence.generic_knowledge.contracts import AccountingState, ApplicabilityKey
from insurance_intelligence.generic_knowledge.resolution_status import ComputedResolution, ResolutionStatus


class WaitingPeriodComparisonProjectionError(ValueError):
    pass


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodComparisonProjectionError(f"{field_name} must be non-empty text")
    return value.strip()


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise WaitingPeriodComparisonProjectionError(f"{field_name} must be a tuple")
    cleaned = tuple(_text(value, field_name) for value in values)
    if len(cleaned) != len(set(cleaned)):
        raise WaitingPeriodComparisonProjectionError(f"{field_name} must not contain duplicates")
    return cleaned


def _blocked(
    *,
    concept_id: str,
    dimension_id: str,
    applicability: ApplicabilityKey,
    evidence_ids: tuple[str, ...],
    reason_code: NotComparableReasonCode,
    blocking_reasons: tuple[str, ...],
    producer_state: str,
) -> NotComparableDimension:
    return NotComparableDimension(
        concept_id=concept_id,
        dimension_id=dimension_id,
        source_family="WAITING_PERIOD",
        applicability=applicability,
        evidence_ids=evidence_ids,
        reason_code=reason_code,
        blocking_reasons=blocking_reasons,
        producer_state=producer_state,
    )


def project_waiting_period_dimension(
    *,
    concept_id: str,
    dimension_id: str,
    applicability: ApplicabilityKey,
    evidence_ids: tuple[str, ...],
    accounting_state: AccountingState,
    resolution: ComputedResolution,
    structured_value: Mapping[str, Any] | None,
    material_residue_reasons: tuple[str, ...] = (),
    publication_blockers: tuple[str, ...] = (),
) -> ComparisonDimensionProjection:
    """Project one waiting-period dimension without permitting unresolved values to compare."""

    concept_id = _text(concept_id, "concept_id")
    dimension_id = _text(dimension_id, "dimension_id")
    if not isinstance(applicability, ApplicabilityKey):
        raise WaitingPeriodComparisonProjectionError("applicability must be ApplicabilityKey")
    evidence_ids = _text_tuple(evidence_ids, "evidence_ids")
    if not evidence_ids:
        raise WaitingPeriodComparisonProjectionError("evidence_ids must not be empty")
    if not isinstance(accounting_state, AccountingState):
        raise WaitingPeriodComparisonProjectionError("accounting_state must be AccountingState")
    if not isinstance(resolution, ComputedResolution):
        raise WaitingPeriodComparisonProjectionError("resolution must be ComputedResolution")
    material_residue_reasons = _text_tuple(material_residue_reasons, "material_residue_reasons")
    publication_blockers = _text_tuple(publication_blockers, "publication_blockers")

    if accounting_state is AccountingState.EXPLICITLY_NON_APPLICABLE:
        return NotApplicableDimension(
            concept_id=concept_id,
            dimension_id=dimension_id,
            source_family="WAITING_PERIOD",
            applicability=applicability,
            evidence_ids=evidence_ids,
            reason_code=NotApplicableReasonCode.EXPLICITLY_NON_APPLICABLE,
            reason="Governed source accounting explicitly establishes that this waiting-period dimension does not apply.",
        )

    if accounting_state is not AccountingState.MAPPED:
        reason_code = (
            NotComparableReasonCode.MATERIAL_RESIDUE
            if accounting_state in {
                AccountingState.NOT_YET_REPRESENTABLE,
                AccountingState.CONFLICTED,
                AccountingState.DEFERRED_WITH_REASON,
            }
            else NotComparableReasonCode.GOVERNANCE_BLOCKED
        )
        return _blocked(
            concept_id=concept_id,
            dimension_id=dimension_id,
            applicability=applicability,
            evidence_ids=evidence_ids,
            reason_code=reason_code,
            blocking_reasons=(f"waiting-period accounting state is {accounting_state.value}",),
            producer_state=accounting_state.value,
        )

    if material_residue_reasons:
        return _blocked(
            concept_id=concept_id,
            dimension_id=dimension_id,
            applicability=applicability,
            evidence_ids=evidence_ids,
            reason_code=NotComparableReasonCode.MATERIAL_RESIDUE,
            blocking_reasons=material_residue_reasons,
            producer_state=resolution.status.value,
        )

    if publication_blockers:
        return _blocked(
            concept_id=concept_id,
            dimension_id=dimension_id,
            applicability=applicability,
            evidence_ids=evidence_ids,
            reason_code=NotComparableReasonCode.GOVERNANCE_BLOCKED,
            blocking_reasons=publication_blockers,
            producer_state=resolution.status.value,
        )

    if resolution.status is not ResolutionStatus.RESOLVED:
        return _blocked(
            concept_id=concept_id,
            dimension_id=dimension_id,
            applicability=applicability,
            evidence_ids=evidence_ids,
            reason_code=NotComparableReasonCode.RESOLUTION_BLOCKED,
            blocking_reasons=(
                f"waiting-period semantic resolution is {resolution.status.value}",
            ),
            producer_state=resolution.status.value,
        )

    if not isinstance(structured_value, Mapping) or not structured_value:
        return _blocked(
            concept_id=concept_id,
            dimension_id=dimension_id,
            applicability=applicability,
            evidence_ids=evidence_ids,
            reason_code=NotComparableReasonCode.COMPARISON_READINESS_BLOCKED,
            blocking_reasons=("resolved waiting-period dimension has no governed structured comparison value",),
            producer_state=resolution.status.value,
        )

    return ComparableDimension(
        concept_id=concept_id,
        dimension_id=dimension_id,
        source_family="WAITING_PERIOD",
        applicability=applicability,
        evidence_ids=evidence_ids,
        structured_value=structured_value,
    )


__all__ = [
    "WaitingPeriodComparisonProjectionError",
    "project_waiting_period_dimension",
]
