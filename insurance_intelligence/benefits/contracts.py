"""Typed governed benefit contracts for MO-025B.

These contracts describe canonical benefit identity, product-specific benefit
implementations, structured mechanics, and evidence lineage. They do not
discover, compare, rank, recommend, decide entitlement, or generate customer
answers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from types import MappingProxyType
from typing import Mapping


class BenefitContractError(ValueError):
    """Raised when a governed benefit contract is structurally invalid."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenefitContractError(f"{field_name} must be non-empty text")
    return value.strip()


def _optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field_name)


def _text_tuple(values: tuple[str, ...], field_name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise BenefitContractError(f"{field_name} must be a tuple")
    cleaned = tuple(_required_text(value, f"{field_name}[]") for value in values)
    if not allow_empty and not cleaned:
        raise BenefitContractError(f"{field_name} must not be empty")
    if len(cleaned) != len(set(cleaned)):
        raise BenefitContractError(f"{field_name} must not contain duplicates")
    return cleaned


class ReviewStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class PublicationStatus(str, Enum):
    NOT_PUBLISHED = "NOT_PUBLISHED"
    PUBLISHED = "PUBLISHED"
    WITHDRAWN = "WITHDRAWN"


class BenefitAvailability(str, Enum):
    INCLUDED = "INCLUDED"
    OPTIONAL = "OPTIONAL"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    CONDITIONAL = "CONDITIONAL"


class BenefitImplementationType(str, Enum):
    BUILT_IN = "BUILT_IN"
    OPTIONAL_COVER = "OPTIONAL_COVER"
    RIDER = "RIDER"
    PRODUCT_OPTION = "PRODUCT_OPTION"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class MechanicValueType(str, Enum):
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    TEXT = "TEXT"
    ENUM = "ENUM"
    PERCENTAGE = "PERCENTAGE"
    CURRENCY = "CURRENCY"
    DURATION = "DURATION"


@dataclass(frozen=True)
class BenefitEvidenceReference:
    """Governed lineage reference for one benefit mechanic or implementation."""

    evidence_reference_id: str
    source_document_id: str
    source_sha256: str
    authority_type: str
    evidence_locator: str
    canonical_fact_id: str | None = None
    governed_fact_id: str | None = None
    review_decision_id: str | None = None
    bounded_evidence_identity: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_reference_id", _required_text(self.evidence_reference_id, "evidence_reference_id"))
        object.__setattr__(self, "source_document_id", _required_text(self.source_document_id, "source_document_id"))
        object.__setattr__(self, "authority_type", _required_text(self.authority_type, "authority_type"))
        object.__setattr__(self, "evidence_locator", _required_text(self.evidence_locator, "evidence_locator"))
        object.__setattr__(self, "canonical_fact_id", _optional_text(self.canonical_fact_id, "canonical_fact_id"))
        object.__setattr__(self, "governed_fact_id", _optional_text(self.governed_fact_id, "governed_fact_id"))
        object.__setattr__(self, "review_decision_id", _optional_text(self.review_decision_id, "review_decision_id"))
        object.__setattr__(self, "bounded_evidence_identity", _optional_text(self.bounded_evidence_identity, "bounded_evidence_identity"))
        sha = _required_text(self.source_sha256, "source_sha256").lower()
        if len(sha) != 64 or any(character not in "0123456789abcdef" for character in sha):
            raise BenefitContractError("source_sha256 must be a valid SHA-256")
        object.__setattr__(self, "source_sha256", sha)
        if not any((self.canonical_fact_id, self.governed_fact_id, self.review_decision_id, self.bounded_evidence_identity)):
            raise BenefitContractError("evidence reference must preserve at least one governed lineage identifier")


@dataclass(frozen=True)
class BenefitMechanic:
    """One typed comparison dimension for a product benefit implementation."""

    dimension_id: str
    value_type: MechanicValueType
    value: object
    unit: str | None = None
    applicability: Mapping[str, object] = None  # type: ignore[assignment]
    evidence_reference_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "dimension_id", _required_text(self.dimension_id, "dimension_id"))
        if not isinstance(self.value_type, MechanicValueType):
            raise BenefitContractError("value_type must be a MechanicValueType")
        object.__setattr__(self, "unit", _optional_text(self.unit, "unit"))
        applicability = {} if self.applicability is None else dict(self.applicability)
        object.__setattr__(self, "applicability", MappingProxyType(applicability))
        object.__setattr__(self, "evidence_reference_ids", _text_tuple(self.evidence_reference_ids, "evidence_reference_ids", allow_empty=False))
        self._validate_value()

    def _validate_value(self) -> None:
        if self.value_type is MechanicValueType.BOOLEAN and not isinstance(self.value, bool):
            raise BenefitContractError("BOOLEAN mechanics require bool values")
        if self.value_type is MechanicValueType.INTEGER and (not isinstance(self.value, int) or isinstance(self.value, bool)):
            raise BenefitContractError("INTEGER mechanics require integer values")
        if self.value_type in {MechanicValueType.DECIMAL, MechanicValueType.PERCENTAGE, MechanicValueType.CURRENCY}:
            if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
                raise BenefitContractError(f"{self.value_type.value} mechanics require numeric values")
        if self.value_type in {MechanicValueType.TEXT, MechanicValueType.ENUM, MechanicValueType.DURATION}:
            _required_text(self.value, "value")  # type: ignore[arg-type]
        if self.value_type in {MechanicValueType.CURRENCY, MechanicValueType.DURATION, MechanicValueType.PERCENTAGE} and self.unit is None:
            raise BenefitContractError(f"{self.value_type.value} mechanics require a unit")


@dataclass(frozen=True)
class BenefitConcept:
    """Canonical insurance-benefit identity independent of insurer marketing names."""

    concept_id: str
    canonical_name: str
    definition: str
    benefit_family: str
    allowed_mechanic_dimensions: tuple[str, ...]
    review_status: ReviewStatus
    publication_status: PublicationStatus
    effective_from: date
    effective_to: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "concept_id", _required_text(self.concept_id, "concept_id"))
        object.__setattr__(self, "canonical_name", _required_text(self.canonical_name, "canonical_name"))
        object.__setattr__(self, "definition", _required_text(self.definition, "definition"))
        object.__setattr__(self, "benefit_family", _required_text(self.benefit_family, "benefit_family"))
        object.__setattr__(self, "allowed_mechanic_dimensions", _text_tuple(self.allowed_mechanic_dimensions, "allowed_mechanic_dimensions", allow_empty=False))
        if not isinstance(self.review_status, ReviewStatus):
            raise BenefitContractError("review_status must be a ReviewStatus")
        if not isinstance(self.publication_status, PublicationStatus):
            raise BenefitContractError("publication_status must be a PublicationStatus")
        if not isinstance(self.effective_from, date):
            raise BenefitContractError("effective_from must be a date")
        if self.effective_to is not None and not isinstance(self.effective_to, date):
            raise BenefitContractError("effective_to must be a date or None")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise BenefitContractError("effective_to cannot be before effective_from")

    def is_active(self, as_of: date) -> bool:
        return self.effective_from <= as_of and (self.effective_to is None or as_of <= self.effective_to)

    @property
    def is_governed_for_use(self) -> bool:
        return self.review_status is ReviewStatus.APPROVED and self.publication_status is PublicationStatus.PUBLISHED


@dataclass(frozen=True)
class ProductBenefitImplementation:
    """Governed product-specific implementation of one canonical benefit concept."""

    implementation_id: str
    concept_id: str
    insurer_id: str
    product_id: str
    product_variant_id: str
    marketing_name: str
    availability: BenefitAvailability
    implementation_type: BenefitImplementationType
    mechanics: tuple[BenefitMechanic, ...]
    evidence_references: tuple[BenefitEvidenceReference, ...]
    behaviour_signature_id: str
    conditions: tuple[str, ...]
    limitations: tuple[str, ...]
    exclusions: tuple[str, ...]
    review_status: ReviewStatus
    publication_status: PublicationStatus
    effective_from: date
    effective_to: date | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "implementation_id",
            "concept_id",
            "insurer_id",
            "product_id",
            "product_variant_id",
            "marketing_name",
            "behaviour_signature_id",
        ):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name))
        if not isinstance(self.availability, BenefitAvailability):
            raise BenefitContractError("availability must be a BenefitAvailability")
        if not isinstance(self.implementation_type, BenefitImplementationType):
            raise BenefitContractError("implementation_type must be a BenefitImplementationType")
        if not isinstance(self.review_status, ReviewStatus):
            raise BenefitContractError("review_status must be a ReviewStatus")
        if not isinstance(self.publication_status, PublicationStatus):
            raise BenefitContractError("publication_status must be a PublicationStatus")
        if not isinstance(self.mechanics, tuple) or not self.mechanics:
            raise BenefitContractError("mechanics must be a non-empty tuple")
        if not all(isinstance(item, BenefitMechanic) for item in self.mechanics):
            raise BenefitContractError("mechanics must contain BenefitMechanic values")
        if not isinstance(self.evidence_references, tuple) or not self.evidence_references:
            raise BenefitContractError("evidence_references must be a non-empty tuple")
        if not all(isinstance(item, BenefitEvidenceReference) for item in self.evidence_references):
            raise BenefitContractError("evidence_references must contain BenefitEvidenceReference values")
        dimension_ids = tuple(item.dimension_id for item in self.mechanics)
        if len(dimension_ids) != len(set(dimension_ids)):
            raise BenefitContractError("mechanics must not contain duplicate dimension_id values")
        evidence_ids = tuple(item.evidence_reference_id for item in self.evidence_references)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise BenefitContractError("evidence_references must not contain duplicate IDs")
        known_evidence_ids = set(evidence_ids)
        for mechanic in self.mechanics:
            unknown = set(mechanic.evidence_reference_ids) - known_evidence_ids
            if unknown:
                raise BenefitContractError(f"mechanic references unknown evidence IDs: {sorted(unknown)}")
        object.__setattr__(self, "conditions", _text_tuple(self.conditions, "conditions"))
        object.__setattr__(self, "limitations", _text_tuple(self.limitations, "limitations"))
        object.__setattr__(self, "exclusions", _text_tuple(self.exclusions, "exclusions"))
        if not isinstance(self.effective_from, date):
            raise BenefitContractError("effective_from must be a date")
        if self.effective_to is not None and not isinstance(self.effective_to, date):
            raise BenefitContractError("effective_to must be a date or None")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise BenefitContractError("effective_to cannot be before effective_from")
        if self.availability is BenefitAvailability.NOT_AVAILABLE and self.implementation_type is not BenefitImplementationType.NOT_APPLICABLE:
            raise BenefitContractError("NOT_AVAILABLE benefits must use NOT_APPLICABLE implementation type")

    def is_active(self, as_of: date) -> bool:
        return self.effective_from <= as_of and (self.effective_to is None or as_of <= self.effective_to)

    @property
    def is_governed_for_use(self) -> bool:
        return self.review_status is ReviewStatus.APPROVED and self.publication_status is PublicationStatus.PUBLISHED

    def validate_against(self, concept: BenefitConcept) -> None:
        if self.concept_id != concept.concept_id:
            raise BenefitContractError("implementation concept_id does not match concept")
        allowed = set(concept.allowed_mechanic_dimensions)
        unknown = {item.dimension_id for item in self.mechanics} - allowed
        if unknown:
            raise BenefitContractError(f"implementation contains dimensions not allowed by concept: {sorted(unknown)}")


__all__ = [
    "BenefitAvailability",
    "BenefitConcept",
    "BenefitContractError",
    "BenefitEvidenceReference",
    "BenefitImplementationType",
    "BenefitMechanic",
    "MechanicValueType",
    "ProductBenefitImplementation",
    "PublicationStatus",
    "ReviewStatus",
]
