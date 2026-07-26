"""Health-owned room-category taxonomy and conservative eligibility comparator.

This module is intentionally limited to category semantics.  It does not infer
claim admissibility, monetary loss, proportionate deduction, or hospital tariff
mapping.  It is a reusable domain adapter for room-category constraints such as
"Single Private A.C. Room".
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RoomCategory(StrEnum):
    GENERAL_WARD = "general_ward"
    TWIN_SHARING_AC_ROOM = "twin_sharing_ac_room"
    SINGLE_PRIVATE_NON_AC_ROOM = "single_private_non_ac_room"
    SINGLE_PRIVATE_AC_ROOM = "single_private_ac_room"
    DELUXE_PRIVATE_AC_ROOM = "deluxe_private_ac_room"
    SUITE_ROOM = "suite_room"
    INTENSIVE_CARE_UNIT = "intensive_care_unit"


class RoomEligibilityStatus(StrEnum):
    """Result of comparing a supplied room category with a policy entitlement.

    ``POTENTIALLY_ABOVE_ENTITLEMENT`` deliberately does not say a monetary
    deduction will apply.  It only says the supplied category is above the
    stated room-category entitlement in this reviewed taxonomy.
    """

    WITHIN_ENTITLEMENT = "within_entitlement"
    POTENTIALLY_ABOVE_ENTITLEMENT = "potentially_above_entitlement"
    ICU_SEPARATE_RULE = "icu_separate_rule"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class RoomCategoryAssessment:
    selected_room_category: RoomCategory | None
    eligible_room_category: RoomCategory | None
    status: RoomEligibilityStatus
    reason: str


# Domain-owned canonical aliases.  Matching is deliberately exact after basic
# whitespace/case normalization; no fuzzy matching is permitted.
_ALIASES: dict[str, RoomCategory] = {
    "general ward": RoomCategory.GENERAL_WARD,
    "general_ward": RoomCategory.GENERAL_WARD,
    "twin sharing ac room": RoomCategory.TWIN_SHARING_AC_ROOM,
    "twin_sharing_ac_room": RoomCategory.TWIN_SHARING_AC_ROOM,
    "single private room": RoomCategory.SINGLE_PRIVATE_NON_AC_ROOM,
    "single private non ac room": RoomCategory.SINGLE_PRIVATE_NON_AC_ROOM,
    "single_private_non_ac_room": RoomCategory.SINGLE_PRIVATE_NON_AC_ROOM,
    "single private ac room": RoomCategory.SINGLE_PRIVATE_AC_ROOM,
    "single private a c room": RoomCategory.SINGLE_PRIVATE_AC_ROOM,
    "single_private_ac_room": RoomCategory.SINGLE_PRIVATE_AC_ROOM,
    "deluxe private ac room": RoomCategory.DELUXE_PRIVATE_AC_ROOM,
    "deluxe private a c room": RoomCategory.DELUXE_PRIVATE_AC_ROOM,
    "deluxe_private_ac_room": RoomCategory.DELUXE_PRIVATE_AC_ROOM,
    "suite room": RoomCategory.SUITE_ROOM,
    "suite": RoomCategory.SUITE_ROOM,
    "suite_room": RoomCategory.SUITE_ROOM,
    "icu": RoomCategory.INTENSIVE_CARE_UNIT,
    "intensive care unit": RoomCategory.INTENSIVE_CARE_UNIT,
    "intensive_care_unit": RoomCategory.INTENSIVE_CARE_UNIT,
}

# The order models only the reviewed non-ICU hierarchy.  ICU is deliberately
# excluded because it is governed by a separate policy rule family.
_NON_ICU_RANK: dict[RoomCategory, int] = {
    RoomCategory.GENERAL_WARD: 10,
    RoomCategory.TWIN_SHARING_AC_ROOM: 20,
    RoomCategory.SINGLE_PRIVATE_NON_AC_ROOM: 30,
    RoomCategory.SINGLE_PRIVATE_AC_ROOM: 40,
    RoomCategory.DELUXE_PRIVATE_AC_ROOM: 50,
    RoomCategory.SUITE_ROOM: 60,
}


def normalize_room_category(raw_value: str) -> RoomCategory | None:
    """Return a reviewed canonical room category or ``None`` for unknown text."""
    normalized = " ".join(raw_value.strip().lower().replace(".", " ").replace("-", " ").replace("_", " ").split())
    return _ALIASES.get(normalized)


def assess_room_category_eligibility(
    *,
    selected_room_category: str,
    eligible_room_category: str,
    icu_stay: bool = False,
) -> RoomCategoryAssessment:
    """Compare one supplied room category with one policy category entitlement.

    This evaluates category positioning only.  It never determines claim
    payment, room-rent cap, proportionate deduction, or insurer liability.
    """
    selected = normalize_room_category(selected_room_category)
    eligible = normalize_room_category(eligible_room_category)
    if selected is None or eligible is None:
        return RoomCategoryAssessment(
            selected_room_category=selected,
            eligible_room_category=eligible,
            status=RoomEligibilityStatus.INDETERMINATE,
            reason="The selected or eligible room category is not in the reviewed Health room-category taxonomy.",
        )
    if icu_stay or selected is RoomCategory.INTENSIVE_CARE_UNIT:
        return RoomCategoryAssessment(
            selected_room_category=selected,
            eligible_room_category=eligible,
            status=RoomEligibilityStatus.ICU_SEPARATE_RULE,
            reason="ICU is governed by a separate ICU rule or exception and must not be evaluated through the ordinary room-category hierarchy.",
        )
    if eligible is RoomCategory.INTENSIVE_CARE_UNIT:
        return RoomCategoryAssessment(
            selected_room_category=selected,
            eligible_room_category=eligible,
            status=RoomEligibilityStatus.INDETERMINATE,
            reason="An ICU-only entitlement cannot be compared through the ordinary room-category hierarchy.",
        )
    if _NON_ICU_RANK[selected] <= _NON_ICU_RANK[eligible]:
        return RoomCategoryAssessment(
            selected_room_category=selected,
            eligible_room_category=eligible,
            status=RoomEligibilityStatus.WITHIN_ENTITLEMENT,
            reason="The selected room category is at or below the reviewed policy entitlement category.",
        )
    return RoomCategoryAssessment(
        selected_room_category=selected,
        eligible_room_category=eligible,
        status=RoomEligibilityStatus.POTENTIALLY_ABOVE_ENTITLEMENT,
        reason="The selected room category is above the reviewed policy entitlement category; financial consequences require separate evidence and calculation rules.",
    )
