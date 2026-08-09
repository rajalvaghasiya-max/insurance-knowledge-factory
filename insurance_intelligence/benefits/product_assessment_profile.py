"""Governed per-product benefit assessment profile for MO-026F.

A profile groups already-governed dimension assessments for one exact product
identity. It is an education-first structure: it exposes strengths, restrictions,
unknowns, protection-floor warnings, and interaction warnings without computing an
overall product score, rank, winner, suitability conclusion, or recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentBand,
    AssessmentStatus,
    BenefitAssessment,
    DecisionRole,
    InteractionSeverity,
)


class ProductAssessmentProfileError(ValueError):
    """Raised when a product assessment profile violates a governance invariant."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProductAssessmentProfileError(f"{field_name} must be non-empty text")
    return value.strip()


class ProfileDimensionDisposition(str, Enum):
    STRENGTH = "STRENGTH"
    NEUTRAL = "NEUTRAL"
    RESTRICTION = "RESTRICTION"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class ProductAssessmentEntry:
    """Bind one exact governed assessment to one exact product identity."""

    product_reference: str
    assessment: BenefitAssessment

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "product_reference",
            _required_text(self.product_reference, "product_reference"),
        )
        if type(self.assessment) is not BenefitAssessment:
            raise ProductAssessmentProfileError(
                "assessment must be the exact BenefitAssessment type"
            )

    @property
    def disposition(self) -> ProfileDimensionDisposition:
        if self.assessment.status is AssessmentStatus.NOT_SCORABLE:
            return ProfileDimensionDisposition.UNKNOWN
        if self.assessment.status is AssessmentStatus.NOT_APPLICABLE:
            return ProfileDimensionDisposition.NOT_APPLICABLE
        if self.assessment.assessment_band in {
            AssessmentBand.VERY_STRONG,
            AssessmentBand.STRONG,
        }:
            return ProfileDimensionDisposition.STRENGTH
        if self.assessment.assessment_band is AssessmentBand.MODERATE:
            return ProfileDimensionDisposition.NEUTRAL
        if self.assessment.assessment_band in {
            AssessmentBand.RESTRICTIVE,
            AssessmentBand.VERY_RESTRICTIVE,
        }:
            return ProfileDimensionDisposition.RESTRICTION
        raise ProductAssessmentProfileError(
            "assessed entry has no supported disposition"
        )


@dataclass(frozen=True)
class GovernedProductBenefitAssessmentProfile:
    profile_id: str
    insurer_id: str
    product_id: str
    product_variant_id: str
    product_uin: str
    entries: tuple[ProductAssessmentEntry, ...]
    contract_version: str = "1.0"

    def __post_init__(self) -> None:
        for field_name in (
            "profile_id",
            "insurer_id",
            "product_id",
            "product_variant_id",
            "product_uin",
            "contract_version",
        ):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )
        if not isinstance(self.entries, tuple) or not self.entries:
            raise ProductAssessmentProfileError("entries must be a non-empty tuple")
        if not all(type(item) is ProductAssessmentEntry for item in self.entries):
            raise ProductAssessmentProfileError(
                "entries must contain exact ProductAssessmentEntry values"
            )
        product_reference = self.product_reference
        if any(item.product_reference != product_reference for item in self.entries):
            raise ProductAssessmentProfileError(
                "all entries must be bound to the profile's exact product reference"
            )
        dimension_ids = tuple(item.assessment.dimension_id for item in self.entries)
        if len(dimension_ids) != len(set(dimension_ids)):
            raise ProductAssessmentProfileError(
                "profile must not contain duplicate assessment dimensions"
            )
        ordered = tuple(sorted(self.entries, key=lambda item: item.assessment.dimension_id))
        object.__setattr__(self, "entries", ordered)

    @property
    def product_reference(self) -> str:
        return (
            f"{self.insurer_id}:{self.product_id}:{self.product_variant_id}:{self.product_uin}"
        )

    @property
    def strengths(self) -> tuple[ProductAssessmentEntry, ...]:
        return tuple(
            item
            for item in self.entries
            if item.disposition is ProfileDimensionDisposition.STRENGTH
        )

    @property
    def restrictions(self) -> tuple[ProductAssessmentEntry, ...]:
        return tuple(
            item
            for item in self.entries
            if item.disposition is ProfileDimensionDisposition.RESTRICTION
        )

    @property
    def unknowns(self) -> tuple[ProductAssessmentEntry, ...]:
        return tuple(
            item
            for item in self.entries
            if item.disposition is ProfileDimensionDisposition.UNKNOWN
        )

    @property
    def protection_floor_warnings(self) -> tuple[ProductAssessmentEntry, ...]:
        """Return all material protection-floor restrictions/unknowns; never suppress them."""

        return tuple(
            item
            for item in self.entries
            if item.assessment.decision_role is DecisionRole.PROTECTION_FLOOR
            and item.disposition
            in {
                ProfileDimensionDisposition.RESTRICTION,
                ProfileDimensionDisposition.UNKNOWN,
            }
        )

    @property
    def material_interaction_entries(self) -> tuple[ProductAssessmentEntry, ...]:
        return tuple(
            item
            for item in self.entries
            if any(
                ref.severity in {
                    InteractionSeverity.MATERIAL,
                    InteractionSeverity.CRITICAL,
                }
                for ref in item.assessment.interaction_references
            )
        )


def build_product_assessment_profile(
    *,
    profile_id: str,
    insurer_id: str,
    product_id: str,
    product_variant_id: str,
    product_uin: str,
    entries: tuple[ProductAssessmentEntry, ...],
) -> GovernedProductBenefitAssessmentProfile:
    return GovernedProductBenefitAssessmentProfile(
        profile_id=profile_id,
        insurer_id=insurer_id,
        product_id=product_id,
        product_variant_id=product_variant_id,
        product_uin=product_uin,
        entries=entries,
    )


__all__ = [
    "GovernedProductBenefitAssessmentProfile",
    "ProductAssessmentEntry",
    "ProductAssessmentProfileError",
    "ProfileDimensionDisposition",
    "build_product_assessment_profile",
]
