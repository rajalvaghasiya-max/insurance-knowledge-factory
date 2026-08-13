"""Reviewed proposition contracts for MO-028C.G4.

This layer is the governed interpretation boundary between atomic source inventory and
runtime semantic mapping. It does not parse prose, infer meaning, resolve benefit
identity, map propositions, calculate claims, compare products, or publish facts.

Every asserted semantic dimension must be explicitly bound to governed evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.generic_knowledge.benefit_limit_contracts import (
    CostSharingApplicability,
    CostSharingMechanicType,
    CostSharingOrdering,
    EventScope,
    LimitKind,
    MonetaryAmount,
    PercentageBasis,
    TimeScope,
)
from insurance_intelligence.generic_knowledge.contracts import ApplicabilityKey, EvidenceReference


class ReviewedBenefitLimitPropositionError(ValueError):
    """Raised when a reviewed proposition violates governance invariants."""


class PropositionDimension(str, Enum):
    VALUE_KIND = "VALUE_KIND"
    AMOUNT = "AMOUNT"
    PERCENTAGE = "PERCENTAGE"
    PERCENTAGE_BASIS = "PERCENTAGE_BASIS"
    FLOOR = "FLOOR"
    CEILING = "CEILING"
    TIME_SCOPE = "TIME_SCOPE"
    EVENT_SCOPE = "EVENT_SCOPE"
    SI_BAND = "SI_BAND"
    BENEFIT_LABEL = "BENEFIT_LABEL"
    INTERACTION_APPLICABILITY = "INTERACTION_APPLICABILITY"
    INTERACTION_ORDERING = "INTERACTION_ORDERING"
    INTERACTION_TARGET_SCOPE = "INTERACTION_TARGET_SCOPE"


class InteractionTargetMode(str, Enum):
    EXPLICIT_CONCEPT_SET = "EXPLICIT_CONCEPT_SET"
    PRODUCT_WIDE_GOVERNED_SCOPE = "PRODUCT_WIDE_GOVERNED_SCOPE"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewedBenefitLimitPropositionError(f"{field_name} must be non-empty text")
    return value.strip()


def _evidence_tuple(values: tuple[EvidenceReference, ...]) -> tuple[EvidenceReference, ...]:
    if not isinstance(values, tuple) or not values:
        raise ReviewedBenefitLimitPropositionError("evidence_references must contain evidence")
    if not all(isinstance(value, EvidenceReference) for value in values):
        raise ReviewedBenefitLimitPropositionError(
            "evidence_references must contain EvidenceReference values"
        )
    ids = tuple(item.evidence_id for item in values)
    if len(ids) != len(set(ids)):
        raise ReviewedBenefitLimitPropositionError("evidence_references must have unique evidence_id values")
    return values


@dataclass(frozen=True)
class DimensionEvidenceBinding:
    dimension: PropositionDimension
    evidence_ids: tuple[str, ...]
    review_decision_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.dimension, PropositionDimension):
            raise ReviewedBenefitLimitPropositionError("dimension must be PropositionDimension")
        if not isinstance(self.evidence_ids, tuple) or not self.evidence_ids:
            raise ReviewedBenefitLimitPropositionError("evidence_ids must not be empty")
        normalized = tuple(_text(value, "evidence_ids") for value in self.evidence_ids)
        if len(normalized) != len(set(normalized)):
            raise ReviewedBenefitLimitPropositionError("evidence_ids must be unique")
        object.__setattr__(self, "evidence_ids", normalized)
        object.__setattr__(
            self, "review_decision_id", _text(self.review_decision_id, "review_decision_id")
        )


@dataclass(frozen=True)
class ReviewedBenefitLimitProposition:
    normative_unit_id: str
    raw_benefit_label: str
    limit_kind: LimitKind
    base_applicability: ApplicabilityKey
    evidence_references: tuple[EvidenceReference, ...]
    dimension_evidence_bindings: tuple[DimensionEvidenceBinding, ...]
    review_decision_id: str
    amount: MonetaryAmount | None = None
    percentage: float | None = None
    percentage_basis: PercentageBasis | None = None
    floor_amount: MonetaryAmount | None = None
    ceiling_amount: MonetaryAmount | None = None
    time_scope: TimeScope | None = None
    event_scope: EventScope | None = None
    sum_insured_band_payload: object | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "normative_unit_id", _text(self.normative_unit_id, "normative_unit_id"))
        object.__setattr__(self, "raw_benefit_label", _text(self.raw_benefit_label, "raw_benefit_label"))
        object.__setattr__(self, "review_decision_id", _text(self.review_decision_id, "review_decision_id"))
        if not isinstance(self.limit_kind, LimitKind):
            raise ReviewedBenefitLimitPropositionError("limit_kind must be LimitKind")
        if not isinstance(self.base_applicability, ApplicabilityKey):
            raise ReviewedBenefitLimitPropositionError("base_applicability must be ApplicabilityKey")
        if self.base_applicability.sum_insured_band is not None:
            raise ReviewedBenefitLimitPropositionError(
                "base_applicability.sum_insured_band must be None; typed SI band is separate"
            )
        object.__setattr__(self, "evidence_references", _evidence_tuple(self.evidence_references))
        if not isinstance(self.dimension_evidence_bindings, tuple):
            raise ReviewedBenefitLimitPropositionError("dimension_evidence_bindings must be a tuple")
        if not all(isinstance(value, DimensionEvidenceBinding) for value in self.dimension_evidence_bindings):
            raise ReviewedBenefitLimitPropositionError(
                "dimension_evidence_bindings must contain DimensionEvidenceBinding values"
            )
        dimensions = tuple(item.dimension for item in self.dimension_evidence_bindings)
        if len(dimensions) != len(set(dimensions)):
            raise ReviewedBenefitLimitPropositionError("each proposition dimension may be bound at most once")
        self._validate_shape()
        self._validate_source_sufficiency()

    def _asserted_dimensions(self) -> set[PropositionDimension]:
        asserted = {PropositionDimension.VALUE_KIND, PropositionDimension.BENEFIT_LABEL}
        if self.amount is not None:
            asserted.add(PropositionDimension.AMOUNT)
        if self.percentage is not None:
            asserted.add(PropositionDimension.PERCENTAGE)
        if self.percentage_basis is not None:
            asserted.add(PropositionDimension.PERCENTAGE_BASIS)
        if self.floor_amount is not None:
            asserted.add(PropositionDimension.FLOOR)
        if self.ceiling_amount is not None:
            asserted.add(PropositionDimension.CEILING)
        if self.time_scope is not None:
            asserted.add(PropositionDimension.TIME_SCOPE)
        if self.event_scope is not None:
            asserted.add(PropositionDimension.EVENT_SCOPE)
        if self.sum_insured_band_payload is not None:
            asserted.add(PropositionDimension.SI_BAND)
        return asserted

    def _validate_shape(self) -> None:
        if self.limit_kind is LimitKind.FIXED_CURRENCY:
            if self.amount is None:
                raise ReviewedBenefitLimitPropositionError("FIXED_CURRENCY requires amount")
            if any(value is not None for value in (
                self.percentage, self.percentage_basis, self.floor_amount, self.ceiling_amount
            )):
                raise ReviewedBenefitLimitPropositionError(
                    "FIXED_CURRENCY forbids percentage, basis, floor, and ceiling"
                )
        elif self.limit_kind is LimitKind.PERCENTAGE:
            if self.percentage is None or not isinstance(self.percentage_basis, PercentageBasis):
                raise ReviewedBenefitLimitPropositionError(
                    "PERCENTAGE requires percentage and PercentageBasis"
                )
            if self.amount is not None:
                raise ReviewedBenefitLimitPropositionError("PERCENTAGE forbids amount")
        elif self.limit_kind in (LimitKind.NO_LIMIT, LimitKind.UP_TO_SUM_INSURED):
            if any(value is not None for value in (
                self.amount, self.percentage, self.percentage_basis,
                self.floor_amount, self.ceiling_amount
            )):
                raise ReviewedBenefitLimitPropositionError(
                    f"{self.limit_kind.value} forbids scalar and bound values"
                )
            if self.limit_kind is LimitKind.NO_LIMIT and (
                self.time_scope is not None or self.event_scope is not None
            ):
                raise ReviewedBenefitLimitPropositionError("NO_LIMIT forbids scope fields")

    def _validate_source_sufficiency(self) -> None:
        evidence_ids = {item.evidence_id for item in self.evidence_references}
        binding_by_dimension = {
            item.dimension: item for item in self.dimension_evidence_bindings
        }
        missing = sorted(
            dimension.value
            for dimension in self._asserted_dimensions()
            if dimension not in binding_by_dimension
        )
        if missing:
            raise ReviewedBenefitLimitPropositionError(
                "source-unsupported asserted dimensions: " + ", ".join(missing)
            )
        for binding in self.dimension_evidence_bindings:
            unknown = tuple(value for value in binding.evidence_ids if value not in evidence_ids)
            if unknown:
                raise ReviewedBenefitLimitPropositionError(
                    "dimension evidence binding references unknown evidence_id: "
                    + ", ".join(sorted(unknown))
                )


@dataclass(frozen=True)
class ReviewedCostSharingInteraction:
    normative_unit_id: str
    mechanic_type: CostSharingMechanicType
    applies: CostSharingApplicability
    ordering: CostSharingOrdering
    target_mode: InteractionTargetMode
    evidence_references: tuple[EvidenceReference, ...]
    dimension_evidence_bindings: tuple[DimensionEvidenceBinding, ...]
    review_decision_id: str
    base_applicability: ApplicabilityKey
    target_benefit_concept_ids: tuple[str, ...] = ()
    governed_product_scope_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "normative_unit_id", _text(self.normative_unit_id, "normative_unit_id"))
        object.__setattr__(self, "review_decision_id", _text(self.review_decision_id, "review_decision_id"))
        if not isinstance(self.mechanic_type, CostSharingMechanicType):
            raise ReviewedBenefitLimitPropositionError("mechanic_type must be CostSharingMechanicType")
        if not isinstance(self.applies, CostSharingApplicability):
            raise ReviewedBenefitLimitPropositionError("applies must be CostSharingApplicability")
        if not isinstance(self.ordering, CostSharingOrdering):
            raise ReviewedBenefitLimitPropositionError("ordering must be CostSharingOrdering")
        if not isinstance(self.target_mode, InteractionTargetMode):
            raise ReviewedBenefitLimitPropositionError("target_mode must be InteractionTargetMode")
        if not isinstance(self.base_applicability, ApplicabilityKey):
            raise ReviewedBenefitLimitPropositionError("base_applicability must be ApplicabilityKey")
        object.__setattr__(self, "evidence_references", _evidence_tuple(self.evidence_references))
        if not isinstance(self.dimension_evidence_bindings, tuple) or not all(
            isinstance(value, DimensionEvidenceBinding) for value in self.dimension_evidence_bindings
        ):
            raise ReviewedBenefitLimitPropositionError(
                "dimension_evidence_bindings must contain DimensionEvidenceBinding values"
            )
        if self.applies is not CostSharingApplicability.YES and self.ordering is not CostSharingOrdering.UNKNOWN:
            raise ReviewedBenefitLimitPropositionError(
                "EXEMPT or UNKNOWN interaction applicability requires UNKNOWN ordering"
            )
        if self.target_mode is InteractionTargetMode.EXPLICIT_CONCEPT_SET:
            targets = tuple(_text(value, "target_benefit_concept_ids") for value in self.target_benefit_concept_ids)
            if not targets:
                raise ReviewedBenefitLimitPropositionError(
                    "EXPLICIT_CONCEPT_SET requires target_benefit_concept_ids"
                )
            if any(not value.startswith("health:benefit:") for value in targets):
                raise ReviewedBenefitLimitPropositionError(
                    "interaction targets must be governed health benefit concepts"
                )
            if self.governed_product_scope_id is not None:
                raise ReviewedBenefitLimitPropositionError(
                    "EXPLICIT_CONCEPT_SET forbids governed_product_scope_id"
                )
            object.__setattr__(self, "target_benefit_concept_ids", tuple(sorted(set(targets))))
        else:
            if self.target_benefit_concept_ids:
                raise ReviewedBenefitLimitPropositionError(
                    "PRODUCT_WIDE_GOVERNED_SCOPE forbids explicit target_benefit_concept_ids"
                )
            object.__setattr__(
                self,
                "governed_product_scope_id",
                _text(self.governed_product_scope_id, "governed_product_scope_id"),
            )
        self._validate_source_sufficiency()

    def _validate_source_sufficiency(self) -> None:
        evidence_ids = {item.evidence_id for item in self.evidence_references}
        required = {
            PropositionDimension.INTERACTION_APPLICABILITY,
            PropositionDimension.INTERACTION_TARGET_SCOPE,
        }
        if self.applies is CostSharingApplicability.YES:
            required.add(PropositionDimension.INTERACTION_ORDERING)
        bindings = {item.dimension: item for item in self.dimension_evidence_bindings}
        missing = sorted(d.value for d in required if d not in bindings)
        if missing:
            raise ReviewedBenefitLimitPropositionError(
                "source-unsupported interaction dimensions: " + ", ".join(missing)
            )
        for binding in self.dimension_evidence_bindings:
            unknown = tuple(value for value in binding.evidence_ids if value not in evidence_ids)
            if unknown:
                raise ReviewedBenefitLimitPropositionError(
                    "interaction binding references unknown evidence_id: "
                    + ", ".join(sorted(unknown))
                )


__all__ = [
    "DimensionEvidenceBinding",
    "InteractionTargetMode",
    "PropositionDimension",
    "ReviewedBenefitLimitProposition",
    "ReviewedBenefitLimitPropositionError",
    "ReviewedCostSharingInteraction",
]
