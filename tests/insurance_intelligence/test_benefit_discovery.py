from dataclasses import replace
from datetime import date

import pytest

from insurance_intelligence.benefits.catalogue import RESTORATION_CONCEPT_ID
from insurance_intelligence.benefits.contracts import (
    ProductBenefitImplementation,
    PublicationStatus,
    ReviewStatus,
)
from insurance_intelligence.benefits.discovery import (
    BenefitDiscoveryError,
    BenefitDiscoveryRequest,
    BenefitDiscoveryResult,
    discover_benefits,
)
from insurance_intelligence.benefits.registry import (
    GOVERNED_BENEFIT_IMPLEMENTATIONS,
    registered_benefit_implementations,
)


def test_registry_contains_two_governed_restoration_implementations() -> None:
    implementations = registered_benefit_implementations()

    assert len(implementations) == 2
    assert {item.concept_id for item in implementations} == {RESTORATION_CONCEPT_ID}
    assert all(item.is_governed_for_use for item in implementations)


def test_registry_order_is_deterministic() -> None:
    implementations = registered_benefit_implementations()

    assert tuple(item.insurer_id for item in implementations) == (
        "aditya_birla_health",
        "star_health",
    )
    assert registered_benefit_implementations() == implementations


def test_discovers_both_restoration_implementations() -> None:
    result = discover_benefits(
        BenefitDiscoveryRequest(
            concept_id=RESTORATION_CONCEPT_ID,
            as_of=date(2026, 7, 31),
        )
    )

    assert result.count == 2
    assert not result.is_empty
    assert tuple(item.product_variant_id for item in result.implementations) == (
        "pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324",
        "pv_star_health_star_comprehensive_shahlip26044v092526",
    )


def test_discovery_preserves_product_and_variant_identity() -> None:
    result = discover_benefits(
        BenefitDiscoveryRequest(
            concept_id=RESTORATION_CONCEPT_ID,
            as_of=date(2026, 7, 31),
        )
    )

    identities = {
        (
            item.insurer_id,
            item.product_id,
            item.product_variant_id,
            item.implementation_id,
        )
        for item in result.implementations
    }
    assert identities == {
        (
            "aditya_birla_health",
            "activ_one",
            "pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324",
            "benefit_impl:aditya_birla_health:activ_one_nxt:super_reload:v1",
        ),
        (
            "star_health",
            "star_comprehensive",
            "pv_star_health_star_comprehensive_shahlip26044v092526",
            "benefit_impl:star_health:star_comprehensive:automatic_restoration:v1",
        ),
    }


def test_unknown_concept_returns_explicit_empty_result() -> None:
    result = discover_benefits(
        BenefitDiscoveryRequest(
            concept_id="health:unknown:benefit",
            as_of=date(2026, 7, 31),
        )
    )

    assert isinstance(result, BenefitDiscoveryResult)
    assert result.is_empty
    assert result.count == 0
    assert result.implementations == ()


def test_discovery_filters_unapproved_implementation() -> None:
    unapproved = replace(
        GOVERNED_BENEFIT_IMPLEMENTATIONS[0],
        implementation_id="benefit_impl:test:unapproved:v1",
        review_status=ReviewStatus.REVIEWED,
    )

    result = discover_benefits(
        BenefitDiscoveryRequest(
            concept_id=RESTORATION_CONCEPT_ID,
            as_of=date(2026, 7, 31),
        ),
        registry=(unapproved,),
    )

    assert result.is_empty


def test_discovery_filters_unpublished_implementation() -> None:
    unpublished = replace(
        GOVERNED_BENEFIT_IMPLEMENTATIONS[0],
        implementation_id="benefit_impl:test:unpublished:v1",
        publication_status=PublicationStatus.NOT_PUBLISHED,
    )

    result = discover_benefits(
        BenefitDiscoveryRequest(
            concept_id=RESTORATION_CONCEPT_ID,
            as_of=date(2026, 7, 31),
        ),
        registry=(unpublished,),
    )

    assert result.is_empty


def test_discovery_filters_inactive_implementation_by_effective_date() -> None:
    future = replace(
        GOVERNED_BENEFIT_IMPLEMENTATIONS[0],
        implementation_id="benefit_impl:test:future:v1",
        effective_from=date(2030, 1, 1),
    )

    result = discover_benefits(
        BenefitDiscoveryRequest(
            concept_id=RESTORATION_CONCEPT_ID,
            as_of=date(2026, 7, 31),
        ),
        registry=(future,),
    )

    assert result.is_empty


def test_discovery_includes_effective_date_boundaries() -> None:
    bounded = replace(
        GOVERNED_BENEFIT_IMPLEMENTATIONS[0],
        implementation_id="benefit_impl:test:bounded:v1",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
    )

    first_day = discover_benefits(
        BenefitDiscoveryRequest(
            concept_id=RESTORATION_CONCEPT_ID,
            as_of=date(2026, 1, 1),
        ),
        registry=(bounded,),
    )
    last_day = discover_benefits(
        BenefitDiscoveryRequest(
            concept_id=RESTORATION_CONCEPT_ID,
            as_of=date(2026, 12, 31),
        ),
        registry=(bounded,),
    )

    assert first_day.count == 1
    assert last_day.count == 1


def test_discovery_sorts_supplied_registry_deterministically() -> None:
    result = discover_benefits(
        BenefitDiscoveryRequest(
            concept_id=RESTORATION_CONCEPT_ID,
            as_of=date(2026, 7, 31),
        ),
        registry=tuple(reversed(GOVERNED_BENEFIT_IMPLEMENTATIONS)),
    )

    assert tuple(item.insurer_id for item in result.implementations) == (
        "aditya_birla_health",
        "star_health",
    )


@pytest.mark.parametrize("concept_id", ["", "   "])
def test_request_rejects_blank_concept_id(concept_id: str) -> None:
    with pytest.raises(BenefitDiscoveryError, match="concept_id"):
        BenefitDiscoveryRequest(concept_id=concept_id, as_of=date(2026, 7, 31))


def test_request_rejects_invalid_as_of() -> None:
    with pytest.raises(BenefitDiscoveryError, match="as_of"):
        BenefitDiscoveryRequest(  # type: ignore[arg-type]
            concept_id=RESTORATION_CONCEPT_ID,
            as_of="2026-07-31",
        )


def test_discovery_rejects_invalid_request() -> None:
    with pytest.raises(BenefitDiscoveryError, match="request"):
        discover_benefits(object())  # type: ignore[arg-type]


def test_discovery_rejects_non_tuple_registry() -> None:
    request = BenefitDiscoveryRequest(
        concept_id=RESTORATION_CONCEPT_ID,
        as_of=date(2026, 7, 31),
    )

    with pytest.raises(BenefitDiscoveryError, match="registry must be a tuple"):
        discover_benefits(request, registry=list(GOVERNED_BENEFIT_IMPLEMENTATIONS))  # type: ignore[arg-type]


def test_discovery_rejects_invalid_registry_members() -> None:
    request = BenefitDiscoveryRequest(
        concept_id=RESTORATION_CONCEPT_ID,
        as_of=date(2026, 7, 31),
    )

    with pytest.raises(BenefitDiscoveryError, match="registry must contain"):
        discover_benefits(request, registry=(object(),))  # type: ignore[arg-type]


def test_result_rejects_mismatched_concept() -> None:
    implementation: ProductBenefitImplementation = GOVERNED_BENEFIT_IMPLEMENTATIONS[0]

    with pytest.raises(BenefitDiscoveryError, match="match result concept_id"):
        BenefitDiscoveryResult(
            concept_id="health:other:benefit",
            as_of=date(2026, 7, 31),
            implementations=(implementation,),
        )
