"""Source-limited governed Activ One NXT room-rent publication for MO-026E.

The official insurer product page for UIN ADIHLIP24097V012324 states that Activ One
NXT has no capping on room-rent/ICU and other listed hospitalization expenses up to
the Base Sum Insured. The currently exposed website policy-wording link resolves to
a different product/UIN, so no policy-wording claim about proportionate deduction is
made here. The publication therefore preserves that field as UNKNOWN and must fail
closed at assessment time until authoritative policy-wording evidence is available.
"""
from __future__ import annotations

from datetime import date

from insurance_intelligence.benefits.room_rent_assessment import (
    ProportionateDeductionStatus,
    RoomRentCapType,
)
from insurance_intelligence.benefits.room_rent_publication import (
    GovernedRoomRentFactPublication,
    RoomRentPublicationReviewStatus,
    RoomRentPublicationStatus,
)


ACTIV_ONE_NXT_ROOM_RENT_PUBLICATION = GovernedRoomRentFactPublication(
    publication_id="room_rent_fact:aditya_birla_health:activ_one_nxt:v1",
    insurer_id="aditya_birla_health",
    product_id="activ_one",
    product_variant_id="pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324",
    product_uin="ADIHLIP24097V012324",
    governed_claim=(
        "Activ One NXT has no capping on room rent and ICU charges, with listed base benefits "
        "covered up to Base Sum Insured."
    ),
    cap_type=RoomRentCapType.NO_LIMIT,
    cap_value=None,
    eligible_room_category=None,
    icu_rule="No capping on ICU charges is stated on the official Activ One NXT product page.",
    proportionate_deduction=ProportionateDeductionStatus.UNKNOWN,
    proportionate_deduction_scope=None,
    exceptions=(),
    evidence_reference_id="ev_activ_one_nxt_room_rent_official_product_page",
    source_document_id="aditya_birla_capital_activ_one_nxt_official_product_page",
    source_authority_type="official_insurer_product_page",
    source_locator=(
        "Activ One NXT official product page; product UIN ADIHLIP24097V012324; "
        "key benefits/FAQ state no capping on hospitalization expenses and room-rent/ICU coverage."
    ),
    evidence_text_sha256="336852bc8ab52a60d870695ddef4ed3d8f7230ceaaa984e6441a89a65b07b7c7",
    source_document_sha256=None,
    review_status=RoomRentPublicationReviewStatus.APPROVED,
    publication_status=RoomRentPublicationStatus.PUBLISHED,
    effective_from=date(2026, 8, 9),
    limitations=(
        "This publication is sourced from the official insurer product page, not the policy wording.",
        "Proportionate-deduction applicability remains unresolved until exact-UIN policy-wording evidence is governed.",
        "The policy-wording link exposed on the reviewed product page resolved to a different product/UIN and was rejected.",
        "In-force entitlement remains subject to the Policy Schedule, Product Benefit Table, endorsements, and applicable policy wording.",
    ),
)


__all__ = ["ACTIV_ONE_NXT_ROOM_RENT_PUBLICATION"]
