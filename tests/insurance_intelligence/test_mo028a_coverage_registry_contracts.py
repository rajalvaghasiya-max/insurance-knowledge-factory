import pytest

from insurance_intelligence.coverage_registry.contracts import (
    ConceptCoverageRecord,
    ConceptCoverageStatus,
    CoverageRegistryError,
    EvidenceCoverageStatus,
    InsuranceIntelligenceCoverageRegistry,
    ProductCoverageRecord,
    ProductLifecycleStatus,
)


def concept(
    concept_id: str,
    *,
    status: ConceptCoverageStatus = ConceptCoverageStatus.CERTIFIED,
    comparison_ready: bool = True,
    decision_support_ready: bool = True,
    limitations: tuple[str, ...] = (),
) -> ConceptCoverageRecord:
    evidence = ()
    if status in {
        ConceptCoverageStatus.EVIDENCE_AVAILABLE,
        ConceptCoverageStatus.NORMALIZED,
        ConceptCoverageStatus.GOVERNED,
        ConceptCoverageStatus.CERTIFIED,
        ConceptCoverageStatus.PARTIAL,
        ConceptCoverageStatus.SOURCE_LIMITED,
    }:
        evidence = (f"evidence:{concept_id}",)
    return ConceptCoverageRecord(
        concept_id=concept_id,
        status=status,
        evidence_reference_ids=evidence,
        comparison_ready=comparison_ready,
        decision_support_ready=decision_support_ready,
        limitations=limitations,
    )


def product(
    product_reference: str,
    *,
    insurer_id: str = "star_health",
    product_id: str = "star_comprehensive",
    name: str = "Star Comprehensive",
    uin: str = "TEST-UIN-1",
    lifecycle_status: ProductLifecycleStatus = ProductLifecycleStatus.ACTIVE,
    concepts: tuple[ConceptCoverageRecord, ...] | None = None,
    replacement: str | None = None,
) -> ProductCoverageRecord:
    if concepts is None:
        concepts = (concept("copayment"),)
    known = lifecycle_status is not ProductLifecycleStatus.STATUS_UNKNOWN
    return ProductCoverageRecord(
        product_reference=product_reference,
        insurer_id=insurer_id,
        product_id=product_id,
        canonical_product_name=name,
        uin=uin,
        lifecycle_status=lifecycle_status,
        evidence_status=EvidenceCoverageStatus.COMPLETE,
        concepts=concepts,
        replacement_product_reference=replacement,
        status_evidence_reference_ids=("evidence:lifecycle",) if known else (),
        status_last_verified_at="2026-08-09T18:30:00+05:30" if known else None,
    )


def test_active_product_requires_lifecycle_evidence_and_verification_time() -> None:
    with pytest.raises(CoverageRegistryError, match="requires evidence"):
        ProductCoverageRecord(
            product_reference="star:product:v1",
            insurer_id="star_health",
            product_id="product",
            canonical_product_name="Product",
            uin="UIN1",
            lifecycle_status=ProductLifecycleStatus.ACTIVE,
            evidence_status=EvidenceCoverageStatus.COMPLETE,
            concepts=(),
        )


def test_unknown_lifecycle_is_allowed_without_guessing_evidence() -> None:
    record = product(
        "star:legacy:v1",
        lifecycle_status=ProductLifecycleStatus.STATUS_UNKNOWN,
    )
    assert record.lifecycle_status is ProductLifecycleStatus.STATUS_UNKNOWN
    assert record.status_evidence_reference_ids == ()
    assert record.status_last_verified_at is None


def test_replaced_or_migrated_product_requires_replacement_reference() -> None:
    with pytest.raises(CoverageRegistryError, match="replacement_product_reference"):
        product(
            "star:old:v1",
            lifecycle_status=ProductLifecycleStatus.REPLACED,
        )


def test_source_limited_concept_requires_evidence_and_limitation() -> None:
    with pytest.raises(CoverageRegistryError, match="limitation"):
        concept(
            "room_rent_restriction",
            status=ConceptCoverageStatus.SOURCE_LIMITED,
            comparison_ready=False,
            decision_support_ready=False,
        )


def test_not_automated_concept_cannot_be_downstream_ready() -> None:
    with pytest.raises(CoverageRegistryError, match="cannot be downstream-ready"):
        concept(
            "ped_waiting_period",
            status=ConceptCoverageStatus.NOT_AUTOMATED,
            comparison_ready=True,
            decision_support_ready=False,
            limitations=("Exact governed clause set is not yet automated.",),
        )


def test_decision_support_readiness_requires_comparison_readiness() -> None:
    with pytest.raises(CoverageRegistryError, match="requires comparison readiness"):
        concept(
            "copayment",
            comparison_ready=False,
            decision_support_ready=True,
        )


def test_product_rejects_duplicate_concept_ids() -> None:
    duplicate = (concept("copayment"), concept("copayment"))
    with pytest.raises(CoverageRegistryError, match="duplicate concept_id"):
        product("star:product:v1", concepts=duplicate)


def test_product_exposes_downstream_ready_concepts_without_product_verdict() -> None:
    record = product(
        "star:product:v1",
        concepts=(
            concept("copayment"),
            concept(
                "ped_waiting_period",
                status=ConceptCoverageStatus.NOT_AUTOMATED,
                comparison_ready=False,
                decision_support_ready=False,
                limitations=("Waiting-period semantic gate remains closed.",),
            ),
        ),
    )
    assert record.comparison_ready_concept_ids == ("copayment",)
    assert record.decision_support_ready_concept_ids == ("copayment",)


def test_registry_requires_unique_product_references_and_uins() -> None:
    left = product("star:product:v1", uin="UIN-A")
    right = product(
        "aditya:product:v1",
        insurer_id="aditya_birla_health",
        product_id="activ_one_nxt",
        name="Activ One NXT",
        uin="UIN-A",
    )
    with pytest.raises(CoverageRegistryError, match="UIN values must be unique"):
        InsuranceIntelligenceCoverageRegistry((left, right))


def test_registry_lists_insurers_and_products_deterministically() -> None:
    star = product("star:product:v1", uin="UIN-STAR")
    aditya = product(
        "aditya:product:v1",
        insurer_id="aditya_birla_health",
        product_id="activ_one_nxt",
        name="Activ One NXT",
        uin="UIN-ABHI",
    )
    registry = InsuranceIntelligenceCoverageRegistry((star, aditya))
    assert registry.insurer_ids == ("aditya_birla_health", "star_health")
    assert registry.products_for_insurer("star_health") == (star,)
    assert registry.get_product("aditya:product:v1") == aditya


def test_lifecycle_date_order_is_validated() -> None:
    with pytest.raises(CoverageRegistryError, match="must not be after"):
        ProductCoverageRecord(
            product_reference="star:product:v1",
            insurer_id="star_health",
            product_id="product",
            canonical_product_name="Product",
            uin="UIN1",
            lifecycle_status=ProductLifecycleStatus.DISCONTINUED,
            evidence_status=EvidenceCoverageStatus.COMPLETE,
            concepts=(),
            status_effective_from="2026-08-10",
            status_effective_to="2026-08-09",
            status_evidence_reference_ids=("evidence:lifecycle",),
            status_last_verified_at="2026-08-09T18:30:00+05:30",
        )


def test_contract_has_no_product_quality_or_recommendation_fields() -> None:
    record = product("star:product:v1")
    forbidden = {
        "score",
        "rating",
        "rank",
        "winner",
        "recommendation",
        "suitability",
        "preferred_product",
    }
    assert forbidden.isdisjoint(record.__dataclass_fields__)
