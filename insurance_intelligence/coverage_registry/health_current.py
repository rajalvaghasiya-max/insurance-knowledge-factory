"""Current governed Health coverage registry after MO-028B generic promotions.

This module layers milestone-specific promotions over the immutable MO-028A seed.
Waiting-period promotion is now driven by a governed data manifest plus the generic
G8/G9 migration and G10 publication pipeline. Closed milestone seed records remain
unchanged so historical certification retains its original meaning.
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from insurance_intelligence.coverage_registry.contracts import (
    InsuranceIntelligenceCoverageRegistry,
    ProductCoverageRecord,
)
from insurance_intelligence.coverage_registry.health_seed import (
    ACTIV_ONE_NXT_COVERAGE as MO028A_ACTIV_ONE_NXT_COVERAGE,
    STAR_COMPREHENSIVE_COVERAGE as MO028A_STAR_COMPREHENSIVE_COVERAGE,
)
from insurance_intelligence.generic_knowledge.authority_resolution import AuthorityClass
from insurance_intelligence.generic_knowledge.publication_eligibility import (
    GovernedReviewStatus,
    SourceFreshnessStatus,
)
from insurance_intelligence.generic_knowledge.waiting_period_migration import (
    migrate_waiting_period_record,
)
from insurance_intelligence.generic_knowledge.waiting_period_publication import (
    GovernedWaitingPeriodPublication,
    project_waiting_period_publication_to_coverage,
    publish_waiting_period_migration,
)


_REPO_ROOT = Path(__file__).resolve().parents[2]
_MANIFEST_PATH = (
    _REPO_ROOT
    / "knowledge/factory/migrations/health_waiting_period_publication_manifest_v1.json"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_current_products() -> tuple[
    tuple[ProductCoverageRecord, ...],
    dict[str, GovernedWaitingPeriodPublication],
]:
    manifest = _load_json(_MANIFEST_PATH)
    if manifest.get("record_type") != "generic_waiting_period_publication_manifest_v1":
        raise ValueError("unsupported Health waiting-period publication manifest")

    base_by_reference = {
        MO028A_STAR_COMPREHENSIVE_COVERAGE.product_reference: MO028A_STAR_COMPREHENSIVE_COVERAGE,
        MO028A_ACTIV_ONE_NXT_COVERAGE.product_reference: MO028A_ACTIV_ONE_NXT_COVERAGE,
    }
    current_by_reference = dict(base_by_reference)
    publications: dict[str, GovernedWaitingPeriodPublication] = {}

    for entry in manifest.get("entries", []):
        product_reference = entry["product_reference"]
        if product_reference in publications:
            raise ValueError(f"duplicate publication manifest product: {product_reference}")
        base = base_by_reference.get(product_reference)
        if base is None:
            raise ValueError(
                f"publication manifest references unknown Health product: {product_reference}"
            )

        migration_path = _REPO_ROOT / entry["migration_path"]
        migration = migrate_waiting_period_record(_load_json(migration_path))
        if migration.applicability.product_reference != product_reference:
            raise ValueError(
                "publication manifest product reference does not match migration applicability"
            )

        publication = publish_waiting_period_migration(
            migration,
            publication_id=entry["publication_id"],
            authority_class=AuthorityClass(entry["authority_class"]),
            as_of_date=date.fromisoformat(entry["certification_as_of_date"]),
            review_status=GovernedReviewStatus(entry["review_status"]),
            source_freshness=SourceFreshnessStatus(entry["source_freshness"]),
            regulatory_overlay_version=entry.get("regulatory_overlay_version"),
        )
        publications[product_reference] = publication
        current_by_reference[product_reference] = project_waiting_period_publication_to_coverage(
            base,
            publication,
            comparison_ready=bool(entry["comparison_ready"]),
            decision_support_ready=bool(entry["decision_support_ready"]),
        )

    return tuple(current_by_reference.values()), publications


_CURRENT_PRODUCTS, WAITING_PERIOD_PUBLICATIONS = _build_current_products()

STAR_COMPREHENSIVE_COVERAGE = next(
    product
    for product in _CURRENT_PRODUCTS
    if product.product_reference == MO028A_STAR_COMPREHENSIVE_COVERAGE.product_reference
)
ACTIV_ONE_NXT_COVERAGE = next(
    product
    for product in _CURRENT_PRODUCTS
    if product.product_reference == MO028A_ACTIV_ONE_NXT_COVERAGE.product_reference
)

HEALTH_COVERAGE_REGISTRY = InsuranceIntelligenceCoverageRegistry(_CURRENT_PRODUCTS)


__all__ = [
    "ACTIV_ONE_NXT_COVERAGE",
    "HEALTH_COVERAGE_REGISTRY",
    "STAR_COMPREHENSIVE_COVERAGE",
    "WAITING_PERIOD_PUBLICATIONS",
]
