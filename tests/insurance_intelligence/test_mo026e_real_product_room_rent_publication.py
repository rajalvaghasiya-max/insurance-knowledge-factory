from dataclasses import replace

import pytest

from insurance_intelligence.benefits.activ_one_nxt_room_rent import (
    ACTIV_ONE_NXT_ROOM_RENT_PUBLICATION,
)
from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentStatus,
    DecisionRole,
)
from insurance_intelligence.benefits.room_rent_assessment import (
    ProportionateDeductionStatus,
    RoomRentCapType,
    assess_room_rent_restriction,
)
from insurance_intelligence.benefits.room_rent_publication import (
    RoomRentPublicationError,
    RoomRentPublicationStatus,
    build_room_rent_restriction_from_publication,
)


def test_activ_one_nxt_publication_preserves_exact_product_identity() -> None:
    publication = ACTIV_ONE_NXT_ROOM_RENT_PUBLICATION
    assert publication.insurer_id == "aditya_birla_health"
    assert publication.product_id == "activ_one"
    assert publication.product_variant_id == (
        "pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324"
    )
    assert publication.product_uin == "ADIHLIP24097V012324"
    assert publication.is_governed_for_use is True


def test_activ_one_nxt_publication_is_source_limited_not_policy_wording() -> None:
    publication = ACTIV_ONE_NXT_ROOM_RENT_PUBLICATION
    assert publication.source_authority_type == "official_insurer_product_page"
    assert publication.source_document_sha256 is None
    text = " ".join(publication.limitations).lower()
    assert "not the policy wording" in text
    assert "different product/uin" in text


def test_publication_preserves_no_cap_fact_without_inventing_pd_semantics() -> None:
    publication = ACTIV_ONE_NXT_ROOM_RENT_PUBLICATION
    assert publication.cap_type is RoomRentCapType.NO_LIMIT
    assert publication.cap_value is None
    assert publication.proportionate_deduction is ProportionateDeductionStatus.UNKNOWN
    assert "no capping" in publication.governed_claim.lower()


def test_publication_has_bounded_evidence_identity() -> None:
    publication = ACTIV_ONE_NXT_ROOM_RENT_PUBLICATION
    assert publication.evidence_reference_id == (
        "ev_activ_one_nxt_room_rent_official_product_page"
    )
    assert len(publication.evidence_text_sha256) == 64
    assert publication.source_document_id
    assert publication.source_locator


def test_only_exact_published_contract_crosses_room_rent_gate() -> None:
    with pytest.raises(RoomRentPublicationError, match="exact"):
        build_room_rent_restriction_from_publication(  # type: ignore[arg-type]
            {"product_uin": "ADIHLIP24097V012324"}
        )

    unpublished = replace(
        ACTIV_ONE_NXT_ROOM_RENT_PUBLICATION,
        publication_status=RoomRentPublicationStatus.NOT_PUBLISHED,
    )
    with pytest.raises(RoomRentPublicationError, match="approved and published"):
        build_room_rent_restriction_from_publication(unpublished)


def test_governed_publication_projects_into_active_room_rent_contract() -> None:
    restriction = build_room_rent_restriction_from_publication(
        ACTIV_ONE_NXT_ROOM_RENT_PUBLICATION
    )
    assert restriction.cap_type is RoomRentCapType.NO_LIMIT
    assert restriction.proportionate_deduction is ProportionateDeductionStatus.UNKNOWN
    assert restriction.governed_source_type == "official_insurer_product_page"
    assert restriction.evidence_reference_ids == (
        "ev_activ_one_nxt_room_rent_official_product_page",
    )
    assert "ADIHLIP24097V012324" in restriction.product_reference.lower().replace(
        "adihlip24097v012324", "ADIHLIP24097V012324"
    ) or restriction.product_reference.endswith(
        "pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324"
    )


def test_real_product_assessment_fails_closed_until_pd_is_governed() -> None:
    restriction = build_room_rent_restriction_from_publication(
        ACTIV_ONE_NXT_ROOM_RENT_PUBLICATION
    )
    result = assess_room_rent_restriction(restriction)

    assert result.status is AssessmentStatus.NOT_SCORABLE
    assert result.assessment_band is None
    assert result.decision_role is DecisionRole.PROTECTION_FLOOR
    assert "proportionate-deduction" in result.summary.lower()
    assert result.evidence_reference_ids == (
        "ev_activ_one_nxt_room_rent_official_product_page",
    )


def test_real_product_publication_does_not_create_a_product_verdict() -> None:
    restriction = build_room_rent_restriction_from_publication(
        ACTIV_ONE_NXT_ROOM_RENT_PUBLICATION
    )
    result = assess_room_rent_restriction(restriction)
    forbidden = {
        "overall_score",
        "rank",
        "winner",
        "weight",
        "recommendation",
        "suitability",
    }
    assert forbidden.isdisjoint(result.__dataclass_fields__)
