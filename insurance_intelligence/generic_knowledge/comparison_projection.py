"""Fail-closed projection contract from certified knowledge to comparison.

AR-2.4H2 defines a deliberately small boundary between semantic-family knowledge and
comparison/assessment consumers.  The boundary is a sum type: a consumer receives exactly
one of ``ComparableDimension``, ``NotComparableDimension``, or ``NotApplicableDimension``.
A comparative value exists only on ``ComparableDimension``; readiness is therefore derived
from the variant and cannot disagree with a separately stored boolean/status field.

Semantic-family adapters remain responsible for documenting their producer-state mapping.
They should use ``classify_producer_state`` so any unrecognised future producer state fails
closed to NOT_COMPARABLE instead of defaulting open.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, TypeAlias

from insurance_intelligence.generic_knowledge.contracts import ApplicabilityKey


class ComparisonProjectionError(ValueError):
    """Raised when a comparison projection violates a fail-closed invariant."""


class ProjectionDisposition(str, Enum):
    COMPARABLE = "COMPARABLE"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class NotComparableReasonCode(str, Enum):
    """Why a material dimension cannot safely support directional comparison now."""

    RESOLUTION_BLOCKED = "RESOLUTION_BLOCKED"
    COMPARISON_READINESS_BLOCKED = "COMPARISON_READINESS_BLOCKED"
    MATERIAL_RESIDUE = "MATERIAL_RESIDUE"
    APPLICABILITY_CONFLICT = "APPLICABILITY_CONFLICT"
    GOVERNANCE_BLOCKED = "GOVERNANCE_BLOCKED"
    SOURCE_LIMITED = "SOURCE_LIMITED"
    UNMAPPED_PRODUCER_STATE = "UNMAPPED_PRODUCER_STATE"


class NotApplicableReasonCode(str, Enum):
    """Why a governed dimension genuinely does not apply to this product/context."""

    EXPLICITLY_NON_APPLICABLE = "EXPLICITLY_NON_APPLICABLE"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ComparisonProjectionError(f"{field_name} must be non-empty text")
    return value.strip()


def _text_tuple(
    values: tuple[str, ...], field_name: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ComparisonProjectionError(f"{field_name} must be a tuple")
    cleaned = tuple(_text(value, field_name) for value in values)
    if not allow_empty and not cleaned:
        raise ComparisonProjectionError(f"{field_name} must not be empty")
    if len(cleaned) != len(set(cleaned)):
        raise ComparisonProjectionError(f"{field_name} must not contain duplicates")
    return cleaned


def _base_fields(
    concept_id: object,
    dimension_id: object,
    source_family: object,
    applicability: object,
    evidence_ids: tuple[str, ...],
) -> tuple[str, str, str, ApplicabilityKey, tuple[str, ...]]:
    if not isinstance(applicability, ApplicabilityKey):
        raise ComparisonProjectionError("applicability must be an ApplicabilityKey")
    return (
        _text(concept_id, "concept_id"),
        _text(dimension_id, "dimension_id"),
        _text(source_family, "source_family"),
        applicability,
        _text_tuple(evidence_ids, "evidence_ids"),
    )


@dataclass(frozen=True)
class ComparableDimension:
    """A dimension whose complete governed semantics permit directional comparison."""

    concept_id: str
    dimension_id: str
    source_family: str
    applicability: ApplicabilityKey
    evidence_ids: tuple[str, ...]
    structured_value: Mapping[str, Any]

    def __post_init__(self) -> None:
        concept, dimension, family, applicability, evidence = _base_fields(
            self.concept_id,
            self.dimension_id,
            self.source_family,
            self.applicability,
            self.evidence_ids,
        )
        if not isinstance(self.structured_value, Mapping) or not self.structured_value:
            raise ComparisonProjectionError(
                "ComparableDimension requires a non-empty structured_value"
            )
        object.__setattr__(self, "concept_id", concept)
        object.__setattr__(self, "dimension_id", dimension)
        object.__setattr__(self, "source_family", family)
        object.__setattr__(self, "applicability", applicability)
        object.__setattr__(self, "evidence_ids", evidence)
        object.__setattr__(
            self, "structured_value", MappingProxyType(dict(self.structured_value))
        )

    @property
    def disposition(self) -> ProjectionDisposition:
        return ProjectionDisposition.COMPARABLE


@dataclass(frozen=True)
class NotComparableDimension:
    """A material dimension that exists but cannot safely support comparison now."""

    concept_id: str
    dimension_id: str
    source_family: str
    applicability: ApplicabilityKey
    evidence_ids: tuple[str, ...]
    reason_code: NotComparableReasonCode
    blocking_reasons: tuple[str, ...]
    producer_state: str | None = None

    def __post_init__(self) -> None:
        concept, dimension, family, applicability, evidence = _base_fields(
            self.concept_id,
            self.dimension_id,
            self.source_family,
            self.applicability,
            self.evidence_ids,
        )
        if not isinstance(self.reason_code, NotComparableReasonCode):
            raise ComparisonProjectionError(
                "reason_code must be a NotComparableReasonCode"
            )
        reasons = _text_tuple(self.blocking_reasons, "blocking_reasons")
        state = None if self.producer_state is None else _text(
            self.producer_state, "producer_state"
        )
        object.__setattr__(self, "concept_id", concept)
        object.__setattr__(self, "dimension_id", dimension)
        object.__setattr__(self, "source_family", family)
        object.__setattr__(self, "applicability", applicability)
        object.__setattr__(self, "evidence_ids", evidence)
        object.__setattr__(self, "blocking_reasons", reasons)
        object.__setattr__(self, "producer_state", state)

    @property
    def disposition(self) -> ProjectionDisposition:
        return ProjectionDisposition.NOT_COMPARABLE


@dataclass(frozen=True)
class NotApplicableDimension:
    """A dimension proven by governed evidence not to apply; this is never 'unknown'."""

    concept_id: str
    dimension_id: str
    source_family: str
    applicability: ApplicabilityKey
    evidence_ids: tuple[str, ...]
    reason_code: NotApplicableReasonCode
    reason: str

    def __post_init__(self) -> None:
        concept, dimension, family, applicability, evidence = _base_fields(
            self.concept_id,
            self.dimension_id,
            self.source_family,
            self.applicability,
            self.evidence_ids,
        )
        if not isinstance(self.reason_code, NotApplicableReasonCode):
            raise ComparisonProjectionError(
                "reason_code must be a NotApplicableReasonCode"
            )
        reason = _text(self.reason, "reason")
        object.__setattr__(self, "concept_id", concept)
        object.__setattr__(self, "dimension_id", dimension)
        object.__setattr__(self, "source_family", family)
        object.__setattr__(self, "applicability", applicability)
        object.__setattr__(self, "evidence_ids", evidence)
        object.__setattr__(self, "reason", reason)

    @property
    def disposition(self) -> ProjectionDisposition:
        return ProjectionDisposition.NOT_APPLICABLE


ComparisonDimensionProjection: TypeAlias = (
    ComparableDimension | NotComparableDimension | NotApplicableDimension
)


def classify_producer_state(
    producer_state: object,
    *,
    comparable_states: frozenset[object],
    not_applicable_states: frozenset[object],
) -> ProjectionDisposition:
    """Classify one producer state with a fail-closed default.

    Semantic-family adapters must explicitly enumerate positive comparability and explicit
    non-applicability.  Every other value -- including a valid future state unknown to the
    adapter -- is NOT_COMPARABLE.
    """

    if not isinstance(comparable_states, frozenset):
        raise ComparisonProjectionError("comparable_states must be a frozenset")
    if not isinstance(not_applicable_states, frozenset):
        raise ComparisonProjectionError("not_applicable_states must be a frozenset")
    overlap = comparable_states.intersection(not_applicable_states)
    if overlap:
        raise ComparisonProjectionError(
            "producer states cannot be both comparable and not applicable"
        )
    if producer_state in comparable_states:
        return ProjectionDisposition.COMPARABLE
    if producer_state in not_applicable_states:
        return ProjectionDisposition.NOT_APPLICABLE
    return ProjectionDisposition.NOT_COMPARABLE


__all__ = [
    "ComparableDimension",
    "ComparisonDimensionProjection",
    "ComparisonProjectionError",
    "NotApplicableDimension",
    "NotApplicableReasonCode",
    "NotComparableDimension",
    "NotComparableReasonCode",
    "ProjectionDisposition",
    "classify_producer_state",
]
