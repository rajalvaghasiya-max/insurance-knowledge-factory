"""Generic benefit-limit semantic contracts for MO-028C.G2.

This module represents benefit-limit meaning only. It does not resolve raw labels,
apply product-specific reasoning, calculate customer-specific currency values,
settle claims, compare products, or publish recommendations.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.generic_knowledge.contracts import EvidenceReference


class BenefitLimitContractError(ValueError):
    """Raised when a benefit-limit semantic contract violates an invariant."""


class LimitKind(str, Enum):
    FIXED_CURRENCY = "FIXED_CURRENCY"
    PERCENTAGE = "PERCENTAGE"
    NO_LIMIT = "NO_LIMIT"
    UP_TO_SUM_INSURED = "UP_TO_SUM_INSURED"


class PercentageBasis(str, Enum):
    SUM_INSURED = "SUM_INSURED"


class TimeScope(str, Enum):
    PER_DAY = "PER_DAY"
    PER_POLICY_YEAR = "PER_POLICY_YEAR"
    PER_POLICY_PERIOD = "PER_POLICY_PERIOD"
    LIFETIME = "LIFETIME"
    UNSPECIFIED = "UNSPECIFIED"


class EventScope(str, Enum):
    PER_CLAIM = "PER_CLAIM"
    PER_HOSPITALIZATION = "PER_HOSPITALIZATION"
    PER_EYE = "PER_EYE"
    UNSPECIFIED = "UNSPECIFIED"


class CostSharingMechanicType(str, Enum):
    COPAY = "COPAY"
    DEDUCTIBLE = "DEDUCTIBLE"
    PROPORTIONATE_DEDUCTION = "PROPORTIONATE_DEDUCTION"


class CostSharingApplicability(str, Enum):
    YES = "YES"
    EXEMPT = "EXEMPT"
    UNKNOWN = "UNKNOWN"


class CostSharingOrdering(str, Enum):
    BEFORE_LIMIT = "BEFORE_LIMIT"
    AFTER_LIMIT = "AFTER_LIMIT"
    UNKNOWN = "UNKNOWN"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenefitLimitContractError(f"{field_name} must be non-empty text")
    return value.strip()


def _positive_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BenefitLimitContractError(f"{field_name} must be numeric")
    number = float(value)
    if number <= 0:
        raise BenefitLimitContractError(f"{field_name} must be greater than zero")
    return number


def _evidence_tuple(
    values: tuple[EvidenceReference, ...], field_name: str, *, allow_empty: bool = False
) -> tuple[EvidenceReference, ...]:
    if not isinstance(values, tuple):
        raise BenefitLimitContractError(f"{field_name} must be a tuple")
    if not allow_empty and not values:
        raise BenefitLimitContractError(f"{field_name} must contain evidence")
    if not all(isinstance(value, EvidenceReference) for value in values):
        raise BenefitLimitContractError(
            f"{field_name} must contain EvidenceReference values"
        )
    return values


@dataclass(frozen=True)
class BenefitIdentityReference:
    """Compact immutable reference to a G1-certified benefit identity snapshot."""

    concept_id: str
    alias_registry_version: str
    alias_registry_snapshot_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "concept_id", _text(self.concept_id, "concept_id"))
        object.__setattr__(
            self,
            "alias_registry_version",
            _text(self.alias_registry_version, "alias_registry_version"),
        )
        object.__setattr__(
            self,
            "alias_registry_snapshot_id",
            _text(self.alias_registry_snapshot_id, "alias_registry_snapshot_id"),
        )
        if not self.concept_id.startswith("health:benefit:"):
            raise BenefitLimitContractError(
                "concept_id must reference a governed health benefit concept"
            )


@dataclass(frozen=True)
class MonetaryAmount:
    amount: float
    currency: str = "INR"

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", _positive_number(self.amount, "amount"))
        currency = _text(self.currency, "currency").upper()
        if currency != "INR":
            raise BenefitLimitContractError("G2 supports INR only")
        object.__setattr__(self, "currency", currency)


@dataclass(frozen=True)
class CostSharingInteractionRule:
    mechanic_type: CostSharingMechanicType
    applies: CostSharingApplicability
    ordering: CostSharingOrdering
    evidence_references: tuple[EvidenceReference, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.mechanic_type, CostSharingMechanicType):
            raise BenefitLimitContractError(
                "mechanic_type must be a CostSharingMechanicType"
            )
        if not isinstance(self.applies, CostSharingApplicability):
            raise BenefitLimitContractError(
                "applies must be a CostSharingApplicability"
            )
        if not isinstance(self.ordering, CostSharingOrdering):
            raise BenefitLimitContractError("ordering must be a CostSharingOrdering")
        object.__setattr__(
            self,
            "evidence_references",
            _evidence_tuple(self.evidence_references, "evidence_references"),
        )
        if self.applies is not CostSharingApplicability.YES:
            if self.ordering is not CostSharingOrdering.UNKNOWN:
                raise BenefitLimitContractError(
                    "EXEMPT or UNKNOWN interaction applicability requires UNKNOWN ordering"
                )

    @property
    def equivalence_ready(self) -> bool:
        if self.applies is CostSharingApplicability.UNKNOWN:
            return False
        if self.applies is CostSharingApplicability.EXEMPT:
            return True
        return self.ordering is not CostSharingOrdering.UNKNOWN


@dataclass(frozen=True)
class BenefitLimitMechanic:
    benefit_identity: BenefitIdentityReference
    limit_kind: LimitKind
    ontology_version: str
    core_evidence_references: tuple[EvidenceReference, ...]
    amount: MonetaryAmount | None = None
    percentage: float | None = None
    percentage_basis: PercentageBasis | None = None
    floor_amount: MonetaryAmount | None = None
    ceiling_amount: MonetaryAmount | None = None
    time_scope: TimeScope | None = None
    event_scope: EventScope | None = None
    scope_evidence_references: tuple[EvidenceReference, ...] = ()
    bound_evidence_references: tuple[EvidenceReference, ...] = ()
    cost_sharing_interactions: tuple[CostSharingInteractionRule, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.benefit_identity, BenefitIdentityReference):
            raise BenefitLimitContractError(
                "benefit_identity must be a BenefitIdentityReference"
            )
        if not isinstance(self.limit_kind, LimitKind):
            raise BenefitLimitContractError("limit_kind must be a LimitKind")
        object.__setattr__(
            self, "ontology_version", _text(self.ontology_version, "ontology_version")
        )
        object.__setattr__(
            self,
            "core_evidence_references",
            _evidence_tuple(
                self.core_evidence_references, "core_evidence_references"
            ),
        )
        object.__setattr__(
            self,
            "scope_evidence_references",
            _evidence_tuple(
                self.scope_evidence_references,
                "scope_evidence_references",
                allow_empty=True,
            ),
        )
        object.__setattr__(
            self,
            "bound_evidence_references",
            _evidence_tuple(
                self.bound_evidence_references,
                "bound_evidence_references",
                allow_empty=True,
            ),
        )
        if not isinstance(self.cost_sharing_interactions, tuple):
            raise BenefitLimitContractError("cost_sharing_interactions must be a tuple")
        if not all(
            isinstance(value, CostSharingInteractionRule)
            for value in self.cost_sharing_interactions
        ):
            raise BenefitLimitContractError(
                "cost_sharing_interactions must contain CostSharingInteractionRule values"
            )
        mechanic_types = tuple(
            value.mechanic_type for value in self.cost_sharing_interactions
        )
        if len(mechanic_types) != len(set(mechanic_types)):
            raise BenefitLimitContractError(
                "cost_sharing_interactions must contain at most one rule per mechanic type"
            )

        if self.amount is not None and not isinstance(self.amount, MonetaryAmount):
            raise BenefitLimitContractError("amount must be a MonetaryAmount")
        if self.floor_amount is not None and not isinstance(
            self.floor_amount, MonetaryAmount
        ):
            raise BenefitLimitContractError("floor_amount must be a MonetaryAmount")
        if self.ceiling_amount is not None and not isinstance(
            self.ceiling_amount, MonetaryAmount
        ):
            raise BenefitLimitContractError("ceiling_amount must be a MonetaryAmount")
        if self.time_scope is not None and not isinstance(self.time_scope, TimeScope):
            raise BenefitLimitContractError("time_scope must be a TimeScope")
        if self.event_scope is not None and not isinstance(self.event_scope, EventScope):
            raise BenefitLimitContractError("event_scope must be an EventScope")

        self._validate_kind_shape()
        self._validate_scope_provenance()
        self._validate_bound_provenance()

    def _validate_kind_shape(self) -> None:
        if self.limit_kind is LimitKind.FIXED_CURRENCY:
            if self.amount is None:
                raise BenefitLimitContractError("FIXED_CURRENCY requires amount")
            if any(
                value is not None
                for value in (
                    self.percentage,
                    self.percentage_basis,
                    self.floor_amount,
                    self.ceiling_amount,
                )
            ):
                raise BenefitLimitContractError(
                    "FIXED_CURRENCY forbids percentage, basis, floor, and ceiling"
                )
            return

        if self.limit_kind is LimitKind.PERCENTAGE:
            if self.percentage is None:
                raise BenefitLimitContractError("PERCENTAGE requires percentage")
            object.__setattr__(
                self, "percentage", _positive_number(self.percentage, "percentage")
            )
            if not isinstance(self.percentage_basis, PercentageBasis):
                raise BenefitLimitContractError(
                    "PERCENTAGE requires a PercentageBasis"
                )
            if self.amount is not None:
                raise BenefitLimitContractError("PERCENTAGE forbids amount")
            if (
                self.floor_amount is not None
                and self.ceiling_amount is not None
                and self.floor_amount.amount > self.ceiling_amount.amount
            ):
                raise BenefitLimitContractError("floor_amount must not exceed ceiling_amount")
            return

        if self.limit_kind in (LimitKind.NO_LIMIT, LimitKind.UP_TO_SUM_INSURED):
            if any(
                value is not None
                for value in (
                    self.amount,
                    self.percentage,
                    self.percentage_basis,
                    self.floor_amount,
                    self.ceiling_amount,
                )
            ):
                raise BenefitLimitContractError(
                    f"{self.limit_kind.value} forbids scalar and bound values"
                )
            if self.limit_kind is LimitKind.NO_LIMIT:
                if self.time_scope is not None or self.event_scope is not None:
                    raise BenefitLimitContractError("NO_LIMIT forbids scope fields")
            return

        raise BenefitLimitContractError(f"unsupported limit_kind: {self.limit_kind}")

    def _validate_scope_provenance(self) -> None:
        has_scope = self.time_scope is not None or self.event_scope is not None
        if has_scope and not self.scope_evidence_references:
            raise BenefitLimitContractError(
                "scope fields require scope_evidence_references"
            )
        if not has_scope and self.scope_evidence_references:
            raise BenefitLimitContractError(
                "scope_evidence_references require at least one scope field"
            )

    def _validate_bound_provenance(self) -> None:
        has_bound = self.floor_amount is not None or self.ceiling_amount is not None
        if has_bound and not self.bound_evidence_references:
            raise BenefitLimitContractError(
                "floor/ceiling modifiers require bound_evidence_references"
            )
        if not has_bound and self.bound_evidence_references:
            raise BenefitLimitContractError(
                "bound_evidence_references require floor or ceiling"
            )

    @property
    def is_si_linked(self) -> bool:
        return self.limit_kind in (
            LimitKind.PERCENTAGE,
            LimitKind.UP_TO_SUM_INSURED,
        )

    @property
    def equivalence_ready(self) -> bool:
        if self.time_scope is TimeScope.UNSPECIFIED:
            return False
        if self.event_scope is EventScope.UNSPECIFIED:
            return False
        if not self.cost_sharing_interactions:
            return False
        return all(rule.equivalence_ready for rule in self.cost_sharing_interactions)


__all__ = [
    "BenefitIdentityReference",
    "BenefitLimitContractError",
    "BenefitLimitMechanic",
    "CostSharingApplicability",
    "CostSharingInteractionRule",
    "CostSharingMechanicType",
    "CostSharingOrdering",
    "EventScope",
    "LimitKind",
    "MonetaryAmount",
    "PercentageBasis",
    "TimeScope",
]
