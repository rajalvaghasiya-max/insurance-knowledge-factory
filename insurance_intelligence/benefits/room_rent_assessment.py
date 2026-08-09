"""Room-rent and proportionate-deduction protection-floor assessment for MO-026D.

This module defines the active insurance_intelligence contract used to assess
room-rent restrictions without importing historical knowledge-domain extractors.
It is intentionally evidence-agnostic at this stage: real-product publication
must come from the authoritative governed pipeline before assessment is allowed.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256

from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentBand,
    AssessmentStatus,
    BenefitAssessment,
    BenefitInteractionReference,
    DecisionRole,
    InteractionSeverity,
    InteractionType,
)

ROOM_RENT_ASSESSMENT_POLICY_ID = "assessment_policy:health:room_rent_restriction:v1"
ROOM_RENT_ASSESSMENT_POLICY_VERSION = "1.0"


class RoomRentAssessmentError(ValueError):
    """Raised when structured room-rent semantics are invalid."""


class RoomRentCapType(str, Enum):
    NO_LIMIT = "NO_LIMIT"
    ROOM_CATEGORY = "ROOM_CATEGORY"
    FIXED_DAILY_AMOUNT = "FIXED_DAILY_AMOUNT"
    PERCENTAGE_OF_SUM_INSURED = "PERCENTAGE_OF_SUM_INSURED"


class ProportionateDeductionStatus(str, Enum):
    DOES_NOT_APPLY = "DOES_NOT_APPLY"
    APPLIES = "APPLIES"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class GovernedRoomRentRestriction:
    restriction_id: str
    product_reference: str
    cap_type: RoomRentCapType
    cap_value: str | float | None
    eligible_room_category: str | None
    icu_rule: str | None
    proportionate_deduction: ProportionateDeductionStatus
    proportionate_deduction_scope: str | None
    exceptions: tuple[str, ...]
    evidence_reference_ids: tuple[str, ...]
    governed_source_type: str

    def __post_init__(self) -> None:
        for name in ("restriction_id", "product_reference", "governed_source_type"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise RoomRentAssessmentError(f"{name} must be non-empty text")
            object.__setattr__(self, name, value.strip())
        if not isinstance(self.cap_type, RoomRentCapType):
            raise RoomRentAssessmentError("cap_type must be a RoomRentCapType")
        if not isinstance(self.proportionate_deduction, ProportionateDeductionStatus):
            raise RoomRentAssessmentError(
                "proportionate_deduction must be a ProportionateDeductionStatus"
            )
        if not isinstance(self.exceptions, tuple):
            raise RoomRentAssessmentError("exceptions must be a tuple")
        if not isinstance(self.evidence_reference_ids, tuple) or not self.evidence_reference_ids:
            raise RoomRentAssessmentError("evidence_reference_ids must be a non-empty tuple")
        cleaned_ids = tuple(item.strip() for item in self.evidence_reference_ids if isinstance(item, str) and item.strip())
        if len(cleaned_ids) != len(self.evidence_reference_ids):
            raise RoomRentAssessmentError("evidence_reference_ids must contain non-empty text")
        if len(cleaned_ids) != len(set(cleaned_ids)):
            raise RoomRentAssessmentError("evidence_reference_ids must not contain duplicates")
        object.__setattr__(self, "evidence_reference_ids", cleaned_ids)
        if self.cap_type is RoomRentCapType.NO_LIMIT and self.cap_value is not None:
            raise RoomRentAssessmentError("NO_LIMIT room rent cannot carry cap_value")
        if self.cap_type is RoomRentCapType.ROOM_CATEGORY and not self.eligible_room_category:
            raise RoomRentAssessmentError("ROOM_CATEGORY requires eligible_room_category")
        if self.cap_type in {RoomRentCapType.FIXED_DAILY_AMOUNT, RoomRentCapType.PERCENTAGE_OF_SUM_INSURED} and self.cap_value is None:
            raise RoomRentAssessmentError("monetary/percentage room-rent caps require cap_value")
        if self.proportionate_deduction is ProportionateDeductionStatus.APPLIES and not self.proportionate_deduction_scope:
            raise RoomRentAssessmentError(
                "APPLIES proportionate deduction requires proportionate_deduction_scope"
            )


def _assessment_id(restriction: GovernedRoomRentRestriction) -> str:
    payload = "\x1f".join(
        (
            restriction.restriction_id,
            ROOM_RENT_ASSESSMENT_POLICY_ID,
            ROOM_RENT_ASSESSMENT_POLICY_VERSION,
        )
    )
    return f"assessment-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def assess_room_rent_restriction(
    restriction: GovernedRoomRentRestriction,
) -> BenefitAssessment:
    """Assess structural room-rent exposure without predicting a claim outcome."""

    if type(restriction) is not GovernedRoomRentRestriction:
        raise RoomRentAssessmentError(
            "restriction must be the exact GovernedRoomRentRestriction type"
        )

    limitations: list[str] = []
    interactions: list[BenefitInteractionReference] = []

    if restriction.proportionate_deduction is ProportionateDeductionStatus.UNKNOWN:
        return BenefitAssessment(
            assessment_id=_assessment_id(restriction),
            implementation_id=f"room_rent_restriction:{restriction.restriction_id}",
            concept_id="health:financial_restriction:room_rent",
            dimension_id="room_rent_restriction",
            decision_role=DecisionRole.PROTECTION_FLOOR,
            status=AssessmentStatus.NOT_SCORABLE,
            assessment_band=None,
            assessment_policy_id=ROOM_RENT_ASSESSMENT_POLICY_ID,
            assessment_policy_version=ROOM_RENT_ASSESSMENT_POLICY_VERSION,
            summary="Room-rent assessment is unavailable because proportionate-deduction status is unresolved.",
            practical_meaning=(
                "PolicyScna will not classify a room-rent restriction until it knows whether exceeding the "
                "room entitlement can affect other admissible hospitalization expenses."
            ),
            source_mechanic_ids=(
                "room_rent_limit",
                "room_category_eligibility",
                "proportionate_deduction",
                "proportionate_deduction_scope",
            ),
            evidence_reference_ids=restriction.evidence_reference_ids,
            limitations=(
                "Proportionate-deduction applicability is unresolved on governed evidence.",
            ),
        )

    if restriction.cap_type is RoomRentCapType.NO_LIMIT:
        band = AssessmentBand.VERY_STRONG
        summary = "No governed room-rent cap is present in the assessed terms."
    elif restriction.proportionate_deduction is ProportionateDeductionStatus.APPLIES:
        band = AssessmentBand.VERY_RESTRICTIVE
        summary = (
            "The policy has a room-rent restriction with proportionate deduction applying to associated "
            "hospitalization expenses within the governed scope."
        )
        interactions.append(
            BenefitInteractionReference(
                target_dimension_id="restoration",
                interaction_type=InteractionType.MAY_REDUCE_EFFECT,
                severity=InteractionSeverity.CRITICAL,
                explanation=(
                    "Room-rent-linked proportionate deduction can reduce admissible hospitalization expenses "
                    "before restoration mechanics determine available coverage capacity."
                ),
                source_mechanic_ids=("room_rent_limit", "proportionate_deduction"),
                evidence_reference_ids=restriction.evidence_reference_ids,
            )
        )
    else:
        band = AssessmentBand.RESTRICTIVE
        summary = (
            "The policy has a governed room-rent restriction, but proportionate deduction is documented as not applying."
        )

    if restriction.icu_rule is None:
        limitations.append("No separately governed ICU room-entitlement rule is available in this assessment input.")
    if restriction.exceptions:
        limitations.append("Documented room-rent exceptions must be read together with the restriction.")
    limitations.append(
        "This assessment describes structural policy restrictions only and does not predict the amount payable on any claim."
    )

    return BenefitAssessment(
        assessment_id=_assessment_id(restriction),
        implementation_id=f"room_rent_restriction:{restriction.restriction_id}",
        concept_id="health:financial_restriction:room_rent",
        dimension_id="room_rent_restriction",
        decision_role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.ASSESSED_WITH_LIMITATIONS,
        assessment_band=band,
        assessment_policy_id=ROOM_RENT_ASSESSMENT_POLICY_ID,
        assessment_policy_version=ROOM_RENT_ASSESSMENT_POLICY_VERSION,
        summary=summary,
        practical_meaning=(
            "Room entitlement and proportionate-deduction rules can materially affect claim-time financial exposure. "
            "This protection-floor warning remains visible regardless of later user preferences."
        ),
        source_mechanic_ids=(
            "room_rent_limit",
            "room_category_eligibility",
            "proportionate_deduction",
            "proportionate_deduction_scope",
        ),
        evidence_reference_ids=restriction.evidence_reference_ids,
        limitations=tuple(limitations),
        interaction_references=tuple(interactions),
    )


__all__ = [
    "GovernedRoomRentRestriction",
    "ProportionateDeductionStatus",
    "ROOM_RENT_ASSESSMENT_POLICY_ID",
    "ROOM_RENT_ASSESSMENT_POLICY_VERSION",
    "RoomRentAssessmentError",
    "RoomRentCapType",
    "assess_room_rent_restriction",
]
