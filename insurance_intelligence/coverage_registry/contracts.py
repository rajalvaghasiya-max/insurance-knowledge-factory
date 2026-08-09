"""Governed insurance-intelligence coverage registry contracts for MO-028A.

The registry is an internal inventory of insurer/product/version coverage. It does
not resolve product identity, invent insurance facts, rank products, or make
recommendations. Product lifecycle and downstream readiness remain explicit,
evidence-backed states.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class CoverageRegistryError(ValueError):
    """Raised when a coverage-registry contract violates an invariant."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CoverageRegistryError(f"{field_name} must be non-empty text")
    return value.strip()


def _optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field_name)


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise CoverageRegistryError(f"{field_name} must be a tuple")
    cleaned = tuple(_required_text(item, f"{field_name}[]") for item in values)
    if len(cleaned) != len(set(cleaned)):
        raise CoverageRegistryError(f"{field_name} must not contain duplicates")
    return cleaned


def _iso_date(value: str | None, field_name: str) -> str | None:
    value = _optional_text(value, field_name)
    if value is None:
        return None
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise CoverageRegistryError(f"{field_name} must be an ISO date") from exc
    return value


def _iso_datetime(value: str | None, field_name: str) -> str | None:
    value = _optional_text(value, field_name)
    if value is None:
        return None
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CoverageRegistryError(f"{field_name} must be an ISO datetime") from exc
    return value


class ProductLifecycleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CLOSED_TO_NEW_BUSINESS = "CLOSED_TO_NEW_BUSINESS"
    DISCONTINUED = "DISCONTINUED"
    WITHDRAWN = "WITHDRAWN"
    REPLACED = "REPLACED"
    MIGRATED = "MIGRATED"
    STATUS_UNKNOWN = "STATUS_UNKNOWN"


class EvidenceCoverageStatus(str, Enum):
    MISSING = "MISSING"
    PARTIAL = "PARTIAL"
    AVAILABLE = "AVAILABLE"
    COMPLETE = "COMPLETE"


class ConceptCoverageStatus(str, Enum):
    NOT_COVERED = "NOT_COVERED"
    DISCOVERED = "DISCOVERED"
    EVIDENCE_AVAILABLE = "EVIDENCE_AVAILABLE"
    NORMALIZED = "NORMALIZED"
    GOVERNED = "GOVERNED"
    CERTIFIED = "CERTIFIED"
    PARTIAL = "PARTIAL"
    SOURCE_LIMITED = "SOURCE_LIMITED"
    BLOCKED = "BLOCKED"
    NOT_AUTOMATED = "NOT_AUTOMATED"


@dataclass(frozen=True)
class ConceptCoverageRecord:
    """Coverage/readiness state for one concept on one governed product version."""

    concept_id: str
    status: ConceptCoverageStatus
    evidence_reference_ids: tuple[str, ...] = ()
    comparison_ready: bool = False
    decision_support_ready: bool = False
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "concept_id", _required_text(self.concept_id, "concept_id"))
        if not isinstance(self.status, ConceptCoverageStatus):
            raise CoverageRegistryError("status must be a ConceptCoverageStatus")
        object.__setattr__(
            self,
            "evidence_reference_ids",
            _text_tuple(self.evidence_reference_ids, "evidence_reference_ids"),
        )
        object.__setattr__(self, "limitations", _text_tuple(self.limitations, "limitations"))
        if type(self.comparison_ready) is not bool or type(self.decision_support_ready) is not bool:
            raise CoverageRegistryError("readiness flags must be booleans")

        if self.status in {
            ConceptCoverageStatus.NOT_COVERED,
            ConceptCoverageStatus.DISCOVERED,
            ConceptCoverageStatus.BLOCKED,
            ConceptCoverageStatus.NOT_AUTOMATED,
        } and (self.comparison_ready or self.decision_support_ready):
            raise CoverageRegistryError(
                f"{self.status.value} concepts cannot be downstream-ready"
            )

        if self.status in {
            ConceptCoverageStatus.SOURCE_LIMITED,
            ConceptCoverageStatus.PARTIAL,
            ConceptCoverageStatus.BLOCKED,
            ConceptCoverageStatus.NOT_AUTOMATED,
        } and not self.limitations:
            raise CoverageRegistryError(
                f"{self.status.value} concepts require a limitation"
            )

        if self.decision_support_ready and not self.comparison_ready:
            raise CoverageRegistryError(
                "decision-support readiness requires comparison readiness"
            )

        evidence_expected = self.status in {
            ConceptCoverageStatus.EVIDENCE_AVAILABLE,
            ConceptCoverageStatus.NORMALIZED,
            ConceptCoverageStatus.GOVERNED,
            ConceptCoverageStatus.CERTIFIED,
            ConceptCoverageStatus.PARTIAL,
            ConceptCoverageStatus.SOURCE_LIMITED,
        }
        if evidence_expected and not self.evidence_reference_ids:
            raise CoverageRegistryError(
                f"{self.status.value} concepts require evidence references"
            )


@dataclass(frozen=True)
class ProductCoverageRecord:
    """Coverage inventory for one canonical insurer product/version."""

    product_reference: str
    insurer_id: str
    product_id: str
    canonical_product_name: str
    uin: str
    lifecycle_status: ProductLifecycleStatus
    evidence_status: EvidenceCoverageStatus
    concepts: tuple[ConceptCoverageRecord, ...]
    status_effective_from: str | None = None
    status_effective_to: str | None = None
    replacement_product_reference: str | None = None
    status_evidence_reference_ids: tuple[str, ...] = ()
    status_last_verified_at: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "product_reference",
            "insurer_id",
            "product_id",
            "canonical_product_name",
            "uin",
        ):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )
        if not isinstance(self.lifecycle_status, ProductLifecycleStatus):
            raise CoverageRegistryError("lifecycle_status must be a ProductLifecycleStatus")
        if not isinstance(self.evidence_status, EvidenceCoverageStatus):
            raise CoverageRegistryError("evidence_status must be an EvidenceCoverageStatus")
        if not isinstance(self.concepts, tuple) or not all(
            type(item) is ConceptCoverageRecord for item in self.concepts
        ):
            raise CoverageRegistryError("concepts must contain exact ConceptCoverageRecord values")
        concept_ids = tuple(item.concept_id for item in self.concepts)
        if len(concept_ids) != len(set(concept_ids)):
            raise CoverageRegistryError("concepts must not duplicate concept_id")
        object.__setattr__(
            self,
            "concepts",
            tuple(sorted(self.concepts, key=lambda item: item.concept_id)),
        )

        object.__setattr__(
            self,
            "status_effective_from",
            _iso_date(self.status_effective_from, "status_effective_from"),
        )
        object.__setattr__(
            self,
            "status_effective_to",
            _iso_date(self.status_effective_to, "status_effective_to"),
        )
        if self.status_effective_from and self.status_effective_to:
            if self.status_effective_from > self.status_effective_to:
                raise CoverageRegistryError(
                    "status_effective_from must not be after status_effective_to"
                )
        object.__setattr__(
            self,
            "replacement_product_reference",
            _optional_text(self.replacement_product_reference, "replacement_product_reference"),
        )
        object.__setattr__(
            self,
            "status_evidence_reference_ids",
            _text_tuple(
                self.status_evidence_reference_ids,
                "status_evidence_reference_ids",
            ),
        )
        object.__setattr__(
            self,
            "status_last_verified_at",
            _iso_datetime(self.status_last_verified_at, "status_last_verified_at"),
        )

        if self.lifecycle_status is ProductLifecycleStatus.STATUS_UNKNOWN:
            if self.replacement_product_reference is not None:
                raise CoverageRegistryError(
                    "STATUS_UNKNOWN cannot name a replacement product"
                )
        else:
            if not self.status_evidence_reference_ids or self.status_last_verified_at is None:
                raise CoverageRegistryError(
                    "known lifecycle status requires evidence and verification timestamp"
                )

        if self.lifecycle_status in {
            ProductLifecycleStatus.REPLACED,
            ProductLifecycleStatus.MIGRATED,
        } and self.replacement_product_reference is None:
            raise CoverageRegistryError(
                f"{self.lifecycle_status.value} requires replacement_product_reference"
            )

    @property
    def comparison_ready_concept_ids(self) -> tuple[str, ...]:
        return tuple(item.concept_id for item in self.concepts if item.comparison_ready)

    @property
    def decision_support_ready_concept_ids(self) -> tuple[str, ...]:
        return tuple(item.concept_id for item in self.concepts if item.decision_support_ready)


class InsuranceIntelligenceCoverageRegistry:
    """Validated immutable collection of product coverage records."""

    def __init__(self, products: tuple[ProductCoverageRecord, ...]) -> None:
        if not isinstance(products, tuple) or not all(
            type(item) is ProductCoverageRecord for item in products
        ):
            raise CoverageRegistryError(
                "products must contain exact ProductCoverageRecord values"
            )
        references = tuple(item.product_reference for item in products)
        if len(references) != len(set(references)):
            raise CoverageRegistryError("product_reference values must be unique")
        uins = tuple(item.uin for item in products)
        if len(uins) != len(set(uins)):
            raise CoverageRegistryError("UIN values must be unique in the coverage registry")
        self._products = tuple(
            sorted(products, key=lambda item: (item.insurer_id, item.canonical_product_name, item.uin))
        )

    @property
    def products(self) -> tuple[ProductCoverageRecord, ...]:
        return self._products

    @property
    def insurer_ids(self) -> tuple[str, ...]:
        return tuple(sorted({item.insurer_id for item in self._products}))

    def products_for_insurer(self, insurer_id: str) -> tuple[ProductCoverageRecord, ...]:
        insurer_id = _required_text(insurer_id, "insurer_id")
        return tuple(item for item in self._products if item.insurer_id == insurer_id)

    def get_product(self, product_reference: str) -> ProductCoverageRecord | None:
        product_reference = _required_text(product_reference, "product_reference")
        return next(
            (item for item in self._products if item.product_reference == product_reference),
            None,
        )


__all__ = [
    "ConceptCoverageRecord",
    "ConceptCoverageStatus",
    "CoverageRegistryError",
    "EvidenceCoverageStatus",
    "InsuranceIntelligenceCoverageRegistry",
    "ProductCoverageRecord",
    "ProductLifecycleStatus",
]
