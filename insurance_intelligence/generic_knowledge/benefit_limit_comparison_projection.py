"""Fail-closed benefit-limit adapter into the AR-2.4 comparison projection.

The adapter consumes a typed benefit-limit applicability cell and emits an ontology-neutral
comparison projection only when accounting is mapped, no material blocker remains, and the
mechanic is equivalence-ready.  The structured value is derived from the mechanic itself so a
caller cannot omit scope or cost-sharing interaction semantics while claiming comparability.
"""
from __future__ import annotations

from insurance_intelligence.generic_knowledge.benefit_limit_applicability import (
    BenefitLimitApplicabilityCell,
)
from insurance_intelligence.generic_knowledge.benefit_limit_contracts import BenefitLimitMechanic
from insurance_intelligence.generic_knowledge.comparison_projection import (
    ComparableDimension,
    ComparisonDimensionProjection,
    NotApplicableDimension,
    NotApplicableReasonCode,
    NotComparableDimension,
    NotComparableReasonCode,
)
from insurance_intelligence.generic_knowledge.contracts import AccountingState


class BenefitLimitComparisonProjectionError(ValueError):
    pass


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenefitLimitComparisonProjectionError(f"{field_name} must be non-empty text")
    return value.strip()


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise BenefitLimitComparisonProjectionError(f"{field_name} must be a tuple")
    cleaned = tuple(_text(value, field_name) for value in values)
    if len(cleaned) != len(set(cleaned)):
        raise BenefitLimitComparisonProjectionError(f"{field_name} must not contain duplicates")
    return cleaned


def _amount_value(value):
    if value is None:
        return None
    return {"amount": value.amount, "currency": value.currency}


def _mechanic_value(mechanic: BenefitLimitMechanic, cell: BenefitLimitApplicabilityCell) -> dict:
    band = cell.applicability.sum_insured_band
    interactions = tuple(
        {
            "mechanic_type": rule.mechanic_type.value,
            "applies": rule.applies.value,
            "ordering": rule.ordering.value,
        }
        for rule in mechanic.cost_sharing_interactions
    )
    return {
        "limit_kind": mechanic.limit_kind.value,
        "amount": _amount_value(mechanic.amount),
        "percentage": mechanic.percentage,
        "percentage_basis": (
            mechanic.percentage_basis.value if mechanic.percentage_basis is not None else None
        ),
        "floor_amount": _amount_value(mechanic.floor_amount),
        "ceiling_amount": _amount_value(mechanic.ceiling_amount),
        "time_scope": mechanic.time_scope.value if mechanic.time_scope is not None else None,
        "event_scope": mechanic.event_scope.value if mechanic.event_scope is not None else None,
        "sum_insured_band": (
            None
            if band is None
            else {
                "lower_bound": band.lower_bound,
                "upper_bound": band.upper_bound,
                "lower_inclusive": band.lower_inclusive,
                "upper_inclusive": band.upper_inclusive,
                "currency": band.currency,
                "explicit_unbounded": band.explicit_unbounded,
            }
        ),
        "cost_sharing_interactions": interactions,
        "ontology_version": mechanic.ontology_version,
    }


def _blocked(
    *,
    cell: BenefitLimitApplicabilityCell,
    dimension_id: str,
    evidence_ids: tuple[str, ...],
    reason_code: NotComparableReasonCode,
    blocking_reasons: tuple[str, ...],
    producer_state: str,
) -> NotComparableDimension:
    return NotComparableDimension(
        concept_id=cell.mechanic.benefit_identity.concept_id,
        dimension_id=dimension_id,
        source_family="BENEFIT_LIMIT",
        applicability=cell.applicability.base_applicability,
        evidence_ids=evidence_ids,
        reason_code=reason_code,
        blocking_reasons=blocking_reasons,
        producer_state=producer_state,
    )


def project_benefit_limit_dimension(
    *,
    cell: BenefitLimitApplicabilityCell,
    dimension_id: str,
    evidence_ids: tuple[str, ...],
    accounting_state: AccountingState,
    material_residue_reasons: tuple[str, ...] = (),
    publication_blockers: tuple[str, ...] = (),
) -> ComparisonDimensionProjection:
    """Project one benefit-limit cell without allowing incomplete mechanics to compare."""

    if not isinstance(cell, BenefitLimitApplicabilityCell):
        raise BenefitLimitComparisonProjectionError("cell must be BenefitLimitApplicabilityCell")
    dimension_id = _text(dimension_id, "dimension_id")
    evidence_ids = _text_tuple(evidence_ids, "evidence_ids")
    if not evidence_ids:
        raise BenefitLimitComparisonProjectionError("evidence_ids must not be empty")
    if not isinstance(accounting_state, AccountingState):
        raise BenefitLimitComparisonProjectionError("accounting_state must be AccountingState")
    material_residue_reasons = _text_tuple(material_residue_reasons, "material_residue_reasons")
    publication_blockers = _text_tuple(publication_blockers, "publication_blockers")

    if accounting_state is AccountingState.EXPLICITLY_NON_APPLICABLE:
        return NotApplicableDimension(
            concept_id=cell.mechanic.benefit_identity.concept_id,
            dimension_id=dimension_id,
            source_family="BENEFIT_LIMIT",
            applicability=cell.applicability.base_applicability,
            evidence_ids=evidence_ids,
            reason_code=NotApplicableReasonCode.EXPLICITLY_NON_APPLICABLE,
            reason="Governed source accounting explicitly establishes that this benefit-limit dimension does not apply.",
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
            cell=cell,
            dimension_id=dimension_id,
            evidence_ids=evidence_ids,
            reason_code=reason_code,
            blocking_reasons=(f"benefit-limit accounting state is {accounting_state.value}",),
            producer_state=accounting_state.value,
        )

    if material_residue_reasons:
        return _blocked(
            cell=cell,
            dimension_id=dimension_id,
            evidence_ids=evidence_ids,
            reason_code=NotComparableReasonCode.MATERIAL_RESIDUE,
            blocking_reasons=material_residue_reasons,
            producer_state="MATERIAL_RESIDUE",
        )

    if publication_blockers:
        return _blocked(
            cell=cell,
            dimension_id=dimension_id,
            evidence_ids=evidence_ids,
            reason_code=NotComparableReasonCode.GOVERNANCE_BLOCKED,
            blocking_reasons=publication_blockers,
            producer_state="PUBLICATION_BLOCKED",
        )

    if not cell.mechanic.equivalence_ready:
        return _blocked(
            cell=cell,
            dimension_id=dimension_id,
            evidence_ids=evidence_ids,
            reason_code=NotComparableReasonCode.COMPARISON_READINESS_BLOCKED,
            blocking_reasons=(
                "benefit-limit mechanic is not equivalence-ready; unresolved scope or cost-sharing semantics remain",
            ),
            producer_state="EQUIVALENCE_NOT_READY",
        )

    return ComparableDimension(
        concept_id=cell.mechanic.benefit_identity.concept_id,
        dimension_id=dimension_id,
        source_family="BENEFIT_LIMIT",
        applicability=cell.applicability.base_applicability,
        evidence_ids=evidence_ids,
        structured_value=_mechanic_value(cell.mechanic, cell),
    )


__all__ = [
    "BenefitLimitComparisonProjectionError",
    "project_benefit_limit_dimension",
]
