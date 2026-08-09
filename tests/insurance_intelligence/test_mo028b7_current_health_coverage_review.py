from __future__ import annotations

from pathlib import Path

from insurance_intelligence.coverage_registry.contracts import ConceptCoverageStatus
from insurance_intelligence.coverage_registry.health_current import (
    HEALTH_COVERAGE_REGISTRY as CURRENT_HEALTH_COVERAGE_REGISTRY,
)
from insurance_intelligence.coverage_registry.health_seed import (
    HEALTH_COVERAGE_REGISTRY as MO028A_HEALTH_COVERAGE_REGISTRY,
)
from insurance_intelligence.coverage_registry.reporting import (
    build_coverage_review_report,
    render_coverage_review_markdown,
)
from scripts.render_health_coverage_review import OUTPUT_PATH


def _waiting_status(registry, insurer_id: str) -> ConceptCoverageStatus:
    product = next(item for item in registry.products if item.insurer_id == insurer_id)
    concept = next(item for item in product.concepts if item.concept_id == "waiting_periods")
    return concept.status


def test_closed_seed_remains_not_automated_for_star_waiting_periods() -> None:
    assert _waiting_status(MO028A_HEALTH_COVERAGE_REGISTRY, "star_health") is ConceptCoverageStatus.NOT_AUTOMATED


def test_current_registry_promotes_only_star_waiting_periods() -> None:
    assert _waiting_status(CURRENT_HEALTH_COVERAGE_REGISTRY, "star_health") is ConceptCoverageStatus.CERTIFIED
    assert _waiting_status(CURRENT_HEALTH_COVERAGE_REGISTRY, "aditya_birla_health") is ConceptCoverageStatus.NOT_AUTOMATED


def test_live_review_matches_current_registry() -> None:
    expected = render_coverage_review_markdown(
        build_coverage_review_report(CURRENT_HEALTH_COVERAGE_REGISTRY)
    )
    actual = Path(OUTPUT_PATH).read_text(encoding="utf-8")
    assert actual == expected


def test_live_review_shows_star_waiting_period_progress() -> None:
    rendered = Path(OUTPUT_PATH).read_text(encoding="utf-8")
    assert "| waiting_periods | NOT_AUTOMATED | CERTIFIED |" in rendered
    assert "| star_health | Star Comprehensive Insurance Policy | SHAHLIP26044V092526 | STATUS_UNKNOWN | 4 | 4 | 4 | 3 |" in rendered


def test_live_review_no_longer_lists_star_waiting_period_gap() -> None:
    rendered = Path(OUTPUT_PATH).read_text(encoding="utf-8")
    assert "Base initial, specific-disease, and PED waiting-period clauses are not yet governed for automation." not in rendered
    assert "Waiting-period semantics have not yet been governed for Activ One NXT decision support." in rendered
