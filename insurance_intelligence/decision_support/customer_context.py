"""Customer circumstance, priority, and hard-constraint contracts for MO-027B/C.

These contracts preserve provenance and keep customer facts separate from customer
priorities. Inferred values may be stored for clarification, but they are not
materially actionable until confirmed. No product ranking, suitability verdict,
or recommendation is represented here.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CustomerContextError(ValueError):
    """Raised when customer decision context violates a governance invariant."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CustomerContextError(f"{field_name} must be non-empty text")
    return value.strip()


class CustomerContextProvenance(str, Enum):
    DECLARED = "DECLARED"
    INFERRED = "INFERRED"
    CONFIRMED = "CONFIRMED"


class PriorityImportance(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CONTROLLING = "CONTROLLING"


class ConstraintOperator(str, Enum):
    EQUALS = "EQUALS"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"
    IN = "IN"


@dataclass(frozen=True)
class CustomerCircumstance:
    circumstance_id: str
    subject_reference: str
    value: object
    provenance: CustomerContextProvenance
    raw_statement: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "circumstance_id", _required_text(self.circumstance_id, "circumstance_id"))
        object.__setattr__(self, "subject_reference", _required_text(self.subject_reference, "subject_reference"))
        object.__setattr__(self, "raw_statement", _required_text(self.raw_statement, "raw_statement"))
        if not isinstance(self.provenance, CustomerContextProvenance):
            raise CustomerContextError("provenance must be a CustomerContextProvenance")

    @property
    def is_materially_actionable(self) -> bool:
        return self.provenance in {
            CustomerContextProvenance.DECLARED,
            CustomerContextProvenance.CONFIRMED,
        }


@dataclass(frozen=True)
class CustomerPriority:
    priority_id: str
    dimension_id: str
    importance: PriorityImportance
    provenance: CustomerContextProvenance
    raw_statement: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "priority_id", _required_text(self.priority_id, "priority_id"))
        object.__setattr__(self, "dimension_id", _required_text(self.dimension_id, "dimension_id"))
        object.__setattr__(self, "raw_statement", _required_text(self.raw_statement, "raw_statement"))
        if not isinstance(self.importance, PriorityImportance):
            raise CustomerContextError("importance must be a PriorityImportance")
        if not isinstance(self.provenance, CustomerContextProvenance):
            raise CustomerContextError("provenance must be a CustomerContextProvenance")

    @property
    def is_materially_actionable(self) -> bool:
        return self.provenance in {
            CustomerContextProvenance.DECLARED,
            CustomerContextProvenance.CONFIRMED,
        }


@dataclass(frozen=True)
class CustomerHardConstraint:
    constraint_id: str
    dimension_id: str
    operator: ConstraintOperator
    expected_value: object
    provenance: CustomerContextProvenance
    raw_statement: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "constraint_id", _required_text(self.constraint_id, "constraint_id"))
        object.__setattr__(self, "dimension_id", _required_text(self.dimension_id, "dimension_id"))
        object.__setattr__(self, "raw_statement", _required_text(self.raw_statement, "raw_statement"))
        if not isinstance(self.operator, ConstraintOperator):
            raise CustomerContextError("operator must be a ConstraintOperator")
        if not isinstance(self.provenance, CustomerContextProvenance):
            raise CustomerContextError("provenance must be a CustomerContextProvenance")
        if self.expected_value is None:
            raise CustomerContextError("expected_value must not be None")
        if self.operator is ConstraintOperator.IN:
            if not isinstance(self.expected_value, tuple) or not self.expected_value:
                raise CustomerContextError("IN constraints require a non-empty tuple expected_value")

    @property
    def is_materially_actionable(self) -> bool:
        return self.provenance in {
            CustomerContextProvenance.DECLARED,
            CustomerContextProvenance.CONFIRMED,
        }


@dataclass(frozen=True)
class CustomerDecisionContext:
    context_id: str
    subject_references: tuple[str, ...]
    circumstances: tuple[CustomerCircumstance, ...] = ()
    priorities: tuple[CustomerPriority, ...] = ()
    hard_constraints: tuple[CustomerHardConstraint, ...] = ()
    contract_version: str = "1.0"

    def __post_init__(self) -> None:
        object.__setattr__(self, "context_id", _required_text(self.context_id, "context_id"))
        object.__setattr__(self, "contract_version", _required_text(self.contract_version, "contract_version"))
        if not isinstance(self.subject_references, tuple) or not self.subject_references:
            raise CustomerContextError("subject_references must be a non-empty tuple")
        cleaned_subjects = tuple(_required_text(value, "subject_references[]") for value in self.subject_references)
        if len(cleaned_subjects) != len(set(cleaned_subjects)):
            raise CustomerContextError("subject_references must not contain duplicates")
        object.__setattr__(self, "subject_references", cleaned_subjects)

        typed_sets = (
            ("circumstances", CustomerCircumstance),
            ("priorities", CustomerPriority),
            ("hard_constraints", CustomerHardConstraint),
        )
        for field_name, expected_type in typed_sets:
            values = getattr(self, field_name)
            if not isinstance(values, tuple) or not all(type(item) is expected_type for item in values):
                raise CustomerContextError(f"{field_name} must contain exact {expected_type.__name__} values")

        circumstance_ids = tuple((item.subject_reference, item.circumstance_id) for item in self.circumstances)
        if len(circumstance_ids) != len(set(circumstance_ids)):
            raise CustomerContextError("circumstances must not duplicate subject/circumstance pairs")
        priority_ids = tuple(item.priority_id for item in self.priorities)
        if len(priority_ids) != len(set(priority_ids)):
            raise CustomerContextError("priorities must not contain duplicate priority ids")
        constraint_ids = tuple(item.constraint_id for item in self.hard_constraints)
        if len(constraint_ids) != len(set(constraint_ids)):
            raise CustomerContextError("hard_constraints must not contain duplicate constraint ids")

        unknown_subjects = {
            item.subject_reference for item in self.circumstances
        } - set(self.subject_references)
        if unknown_subjects:
            raise CustomerContextError(
                f"circumstances reference subjects outside the decision context: {sorted(unknown_subjects)}"
            )

    @property
    def actionable_circumstances(self) -> tuple[CustomerCircumstance, ...]:
        return tuple(item for item in self.circumstances if item.is_materially_actionable)

    @property
    def pending_circumstance_confirmations(self) -> tuple[CustomerCircumstance, ...]:
        return tuple(
            item for item in self.circumstances
            if item.provenance is CustomerContextProvenance.INFERRED
        )

    @property
    def actionable_priorities(self) -> tuple[CustomerPriority, ...]:
        return tuple(item for item in self.priorities if item.is_materially_actionable)

    @property
    def pending_priority_confirmations(self) -> tuple[CustomerPriority, ...]:
        return tuple(
            item for item in self.priorities
            if item.provenance is CustomerContextProvenance.INFERRED
        )

    @property
    def actionable_hard_constraints(self) -> tuple[CustomerHardConstraint, ...]:
        return tuple(item for item in self.hard_constraints if item.is_materially_actionable)


__all__ = [
    "ConstraintOperator",
    "CustomerCircumstance",
    "CustomerContextError",
    "CustomerContextProvenance",
    "CustomerDecisionContext",
    "CustomerHardConstraint",
    "CustomerPriority",
    "PriorityImportance",
]
