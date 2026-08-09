"""Governed real-product room-rent fact publication for MO-026E.

This module defines the only admissible bridge from reviewed real-product room-rent
facts into the active MO-026 room-rent assessment contract. Historical extractor
outputs and arbitrary mappings are intentionally rejected.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from insurance_intelligence.benefits.room_rent_assessment import (
    GovernedRoomRentRestriction,
    ProportionateDeductionStatus,
    RoomRentCapType,
)


class RoomRentPublicationError(ValueError):
    """Raised when a room-rent publication is structurally invalid or unusable."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RoomRentPublicationError(f"{field_name} must be non-empty text")
    return value.strip()


def _optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field_name)


def _sha256(value: str, field_name: str) -> str:
    cleaned = _required_text(value, field_name).lower()
    if len(cleaned) != 64 or any(ch not in "0123456789abcdef" for ch in cleaned):
        raise RoomRentPublicationError(f"{field_name} must be a valid SHA-256")
    return cleaned


class RoomRentPublicationReviewStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RoomRentPublicationStatus(str, Enum):
    NOT_PUBLISHED = "NOT_PUBLISHED"
    PUBLISHED = "PUBLISHED"
    WITHDRAWN = "WITHDRAWN"


@dataclass(frozen=True)
class GovernedRoomRentFactPublication:
    publication_id: str
    insurer_id: str
    product_id: str
    product_variant_id: str
    product_uin: str
    governed_claim: str
    cap_type: RoomRentCapType
    cap_value: str | float | None
    eligible_room_category: str | None
    icu_rule: str | None
    proportionate_deduction: ProportionateDeductionStatus
    proportionate_deduction_scope: str | None
    exceptions: tuple[str, ...]
    evidence_reference_id: str
    source_document_id: str
    source_authority_type: str
    source_locator: str
    evidence_text_sha256: str
    source_document_sha256: str | None
    review_status: RoomRentPublicationReviewStatus
    publication_status: RoomRentPublicationStatus
    effective_from: date
    effective_to: date | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "publication_id",
            "insurer_id",
            "product_id",
            "product_variant_id",
            "product_uin",
            "governed_claim",
            "evidence_reference_id",
            "source_document_id",
            "source_authority_type",
            "source_locator",
        ):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        object.__setattr__(
            self,
            "evidence_text_sha256",
            _sha256(self.evidence_text_sha256, "evidence_text_sha256"),
        )
        if self.source_document_sha256 is not None:
            object.__setattr__(
                self,
                "source_document_sha256",
                _sha256(self.source_document_sha256, "source_document_sha256"),
            )
        if not isinstance(self.cap_type, RoomRentCapType):
            raise RoomRentPublicationError("cap_type must be a RoomRentCapType")
        if not isinstance(self.proportionate_deduction, ProportionateDeductionStatus):
            raise RoomRentPublicationError(
                "proportionate_deduction must be a ProportionateDeductionStatus"
            )
        if not isinstance(self.review_status, RoomRentPublicationReviewStatus):
            raise RoomRentPublicationError("review_status must be a RoomRentPublicationReviewStatus")
        if not isinstance(self.publication_status, RoomRentPublicationStatus):
            raise RoomRentPublicationError("publication_status must be a RoomRentPublicationStatus")
        if not isinstance(self.effective_from, date):
            raise RoomRentPublicationError("effective_from must be a date")
        if self.effective_to is not None and not isinstance(self.effective_to, date):
            raise RoomRentPublicationError("effective_to must be a date or None")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise RoomRentPublicationError("effective_to cannot be before effective_from")
        if not isinstance(self.exceptions, tuple) or not all(
            isinstance(item, str) and item.strip() for item in self.exceptions
        ):
            raise RoomRentPublicationError("exceptions must contain non-empty text values")
        if not isinstance(self.limitations, tuple) or not all(
            isinstance(item, str) and item.strip() for item in self.limitations
        ):
            raise RoomRentPublicationError("limitations must contain non-empty text values")
        object.__setattr__(
            self,
            "eligible_room_category",
            _optional_text(self.eligible_room_category, "eligible_room_category"),
        )
        object.__setattr__(self, "icu_rule", _optional_text(self.icu_rule, "icu_rule"))
        object.__setattr__(
            self,
            "proportionate_deduction_scope",
            _optional_text(self.proportionate_deduction_scope, "proportionate_deduction_scope"),
        )
        if self.cap_type is RoomRentCapType.NO_LIMIT and self.cap_value is not None:
            raise RoomRentPublicationError("NO_LIMIT room rent cannot carry cap_value")
        if self.cap_type is RoomRentCapType.ROOM_CATEGORY and self.eligible_room_category is None:
            raise RoomRentPublicationError("ROOM_CATEGORY requires eligible_room_category")
        if self.proportionate_deduction is ProportionateDeductionStatus.APPLIES and self.proportionate_deduction_scope is None:
            raise RoomRentPublicationError(
                "APPLIES proportionate deduction requires proportionate_deduction_scope"
            )

    @property
    def is_governed_for_use(self) -> bool:
        return (
            self.review_status is RoomRentPublicationReviewStatus.APPROVED
            and self.publication_status is RoomRentPublicationStatus.PUBLISHED
        )


def build_room_rent_restriction_from_publication(
    publication: GovernedRoomRentFactPublication,
) -> GovernedRoomRentRestriction:
    """Project one approved/published fact into the MO-026D assessment contract."""

    if type(publication) is not GovernedRoomRentFactPublication:
        raise RoomRentPublicationError(
            "publication must be the exact GovernedRoomRentFactPublication type"
        )
    if not publication.is_governed_for_use:
        raise RoomRentPublicationError(
            "room-rent publication must be approved and published for governed use"
        )
    return GovernedRoomRentRestriction(
        restriction_id=f"restriction:{publication.publication_id}",
        product_reference=(
            f"{publication.insurer_id}:{publication.product_id}:{publication.product_variant_id}"
        ),
        cap_type=publication.cap_type,
        cap_value=publication.cap_value,
        eligible_room_category=publication.eligible_room_category,
        icu_rule=publication.icu_rule,
        proportionate_deduction=publication.proportionate_deduction,
        proportionate_deduction_scope=publication.proportionate_deduction_scope,
        exceptions=publication.exceptions,
        evidence_reference_ids=(publication.evidence_reference_id,),
        governed_source_type=publication.source_authority_type,
        source_limitations=publication.limitations,
    )


__all__ = [
    "GovernedRoomRentFactPublication",
    "RoomRentPublicationError",
    "RoomRentPublicationReviewStatus",
    "RoomRentPublicationStatus",
    "build_room_rent_restriction_from_publication",
]
