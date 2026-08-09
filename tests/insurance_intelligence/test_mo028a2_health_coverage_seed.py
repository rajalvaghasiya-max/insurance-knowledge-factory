from insurance_intelligence.coverage_registry.contracts import (
    ConceptCoverageStatus,
    ProductLifecycleStatus,
)
from insurance_intelligence.coverage_registry.health_seed import (
    ACTIV_ONE_NXT_COVERAGE,
    HEALTH_COVERAGE_REGISTRY,
    STAR_COMPREHENSIVE_COVERAGE,
)


def _concept(product, concept_id):
    return next(item for item in product.concepts if item.concept_id == concept_id)


def test_health_seed_contains_two_governed_products() -> None:
    assert len(HEALTH_COVERAGE_REGISTRY.products) == 2
    assert HEALTH_COVERAGE_REGISTRY.insurer_ids == (
        "aditya_birla_health",
        "star_health",
    )


def test_star_identity_and_uin_are_preserved() -> None:
    assert STAR_COMPREHENSIVE_COVERAGE.product_id == "star_comprehensive"
    assert STAR_COMPREHENSIVE_COVERAGE.uin == "SHAHLIP26044V092526"


def test_activ_one_nxt_identity_and_uin_are_preserved() -> None:
    assert ACTIV_ONE_NXT_COVERAGE.product_id == "activ_one"
    assert ACTIV_ONE_NXT_COVERAGE.uin == "ADIHLIP24097V012324"


def test_lifecycle_remains_unknown_without_governed_lifecycle_evidence() -> None:
    for product in HEALTH_COVERAGE_REGISTRY.products:
        assert product.lifecycle_status is ProductLifecycleStatus.STATUS_UNKNOWN
        assert product.status_evidence_reference_ids == ()
        assert product.status_last_verified_at is None


def test_star_restoration_copayment_and_room_rent_are_ready() -> None:
    expected = {"restoration", "copayment", "room_rent_restriction"}
    assert expected.issubset(set(STAR_COMPREHENSIVE_COVERAGE.comparison_ready_concept_ids))
    assert expected.issubset(set(STAR_COMPREHENSIVE_COVERAGE.decision_support_ready_concept_ids))
    for concept_id in expected:
        assert _concept(STAR_COMPREHENSIVE_COVERAGE, concept_id).status is ConceptCoverageStatus.CERTIFIED


def test_star_waiting_periods_are_explicitly_not_automated() -> None:
    waiting = _concept(STAR_COMPREHENSIVE_COVERAGE, "waiting_periods")
    assert waiting.status is ConceptCoverageStatus.NOT_AUTOMATED
    assert waiting.comparison_ready is False
    assert waiting.decision_support_ready is False
    assert waiting.limitations


def test_activ_one_restoration_is_certified_and_ready() -> None:
    restoration = _concept(ACTIV_ONE_NXT_COVERAGE, "restoration")
    assert restoration.status is ConceptCoverageStatus.CERTIFIED
    assert restoration.comparison_ready is True
    assert restoration.decision_support_ready is True
    assert len(restoration.evidence_reference_ids) == 2


def test_activ_one_room_rent_remains_source_limited_and_not_ready() -> None:
    room_rent = _concept(ACTIV_ONE_NXT_COVERAGE, "room_rent_restriction")
    assert room_rent.status is ConceptCoverageStatus.SOURCE_LIMITED
    assert room_rent.comparison_ready is False
    assert room_rent.decision_support_ready is False
    assert room_rent.evidence_reference_ids == (
        "ev_activ_one_nxt_room_rent_official_product_page",
    )
    assert room_rent.limitations


def test_activ_one_waiting_periods_are_not_automated() -> None:
    waiting = _concept(ACTIV_ONE_NXT_COVERAGE, "waiting_periods")
    assert waiting.status is ConceptCoverageStatus.NOT_AUTOMATED
    assert waiting.limitations


def test_seed_does_not_overstate_complete_product_evidence() -> None:
    assert STAR_COMPREHENSIVE_COVERAGE.evidence_status.value == "PARTIAL"
    assert ACTIV_ONE_NXT_COVERAGE.evidence_status.value == "PARTIAL"


def test_registry_lookup_returns_exact_seed_records() -> None:
    assert (
        HEALTH_COVERAGE_REGISTRY.get_product(STAR_COMPREHENSIVE_COVERAGE.product_reference)
        is STAR_COMPREHENSIVE_COVERAGE
    )
    assert HEALTH_COVERAGE_REGISTRY.products_for_insurer("aditya_birla_health") == (
        ACTIV_ONE_NXT_COVERAGE,
    )
