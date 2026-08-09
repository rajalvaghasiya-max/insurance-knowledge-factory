"""Generalized current Health coverage registry for MO-028B.G10.

This module is the post-generalization projection path. It consumes the existing Health seed
registry plus a governed publication manifest and generic waiting-period migration/publication
components. Historical MO-028A/MO-028B snapshot modules remain unchanged for certification
reproducibility. Product onboarding does not require product-specific branching here.
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
    HEALTH_COVERAGE_REGISTRY as MO028A_HEALTH_COVERAGE_REGISTRY,
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


def _build_generalized_products() -> tuple[
    tuple[ProductCoverageRecord, ...],
    dict[str, GovernedWaitingPeriodPublication],
]:
    manifest = _load_json(_MANIFEST_PATH)
    if manifest.get("record_type") != "generic_waiting_period_publication_manifest_v1":
        raise ValueError("unsupported Health waiting-period publication manifest")

    base_by_reference = {
        product.product_reference: product
        for product in MO028A_HEALTH_COVERAGE_REGISTRY.products
    }
    generalized_by_reference = dict(base_by_reference)
    publications: dict[str, GovernedWaitingPeriodPublication] = {}

    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("publication manifest entries must be a non-empty list")

    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("publication manifest entries must be mappings")
        product_reference = entry["product_reference"]
        if product_reference in publications:
            raise ValueError(f"duplicate publication manifest product: {product_reference}")
        base = base_by_reference.get(product_reference)
        if base is None:
            raise ValueError(
                f"publication manifest references unknown Health product: {product_reference}"
            )

        migration = migrate_waiting_period_record(
            _load_json(_REPO_ROOT / entry["migration_path"])
        )
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
        generalized_by_reference[product_reference] = (
            project_waiting_period_publication_to_coverage(
                base,
                publication,
                comparison_ready=bool(entry["comparison_ready"]),
                decision_support_ready=bool(entry["decision_support_ready"]),
            )
        )

    return tuple(generalized_by_reference.values()), publications


_GENERALIZED_PRODUCTS, WAITING_PERIOD_PUBLICATIONS = _build_generalized_products()
HEALTH_COVERAGE_REGISTRY = InsuranceIntelligenceCoverageRegistry(_GENERALIZED_PRODUCTS)


__all__ = [
    "HEALTH_COVERAGE_REGISTRY",
    "WAITING_PERIOD_PUBLICATIONS",
]
