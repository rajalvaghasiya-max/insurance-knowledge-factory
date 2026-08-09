from __future__ import annotations

from insurance_intelligence.coverage_registry.contracts import ConceptCoverageStatus
from insurance_intelligence.coverage_registry.health_seed import (
    ACTIV_ONE_NXT_COVERAGE,
    HEALTH_COVERAGE_REGISTRY,
    STAR_COMPREHENSIVE_COVERAGE,
)


def _concept(product, concept_id: str):
    return next(item for item in product.concepts if item.concept_id == concept_id)


def test_star_waiting_periods_are_promoted_to_certified_coverage() -> None:
    waiting = _concept(STAR_COMPREHENSIVE_COVERAGE, "waiting_periods")

    assert waiting.status is ConceptCoverageStatus.CERTIFIED
    assert waiting.evidence_reference_ids
    assert waiting.comparison_ready is True


def test_star_waiting_periods_are_not_yet_decision_support_ready() -> None:
    waiting = _concept(STAR_COMPREHENSIVE_COVERAGE, "waiting_periods")

    assert waiting.decision_support_ready is False
    assert any("assessment policy" in item for item in waiting.limitations)


def test_optional_waiting_period_modifications_are_not_claimed_complete() -> None:
    waiting = _concept(STAR_COMPREHENSIVE_COVERAGE, "waiting_periods")

    assert any("Optional waiting-period modifications" in item for item in waiting.limitations)


def test_activ_one_waiting_periods_remain_not_automated() -> None:
    waiting = _concept(ACTIV_ONE_NXT_COVERAGE, "waiting_periods")

    assert waiting.status is ConceptCoverageStatus.NOT_AUTOMATED
    assert waiting.comparison_ready is False
    assert waiting.decision_support_ready is False


def test_registry_preserves_both_product_states() -> None:
    star = HEALTH_COVERAGE_REGISTRY.get_product(STAR_COMPREHENSIVE_COVERAGE.product_reference)
    activ = HEALTH_COVERAGE_REGISTRY.get_product(ACTIV_ONE_NXT_COVERAGE.product_reference)

    assert star is STAR_COMPREHENSIVE_COVERAGE
    assert activ is ACTIV_ONE_NXT_COVERAGE
    assert _concept(star, "waiting_periods").status is ConceptCoverageStatus.CERTIFIED
    assert _concept(activ, "waiting_periods").status is ConceptCoverageStatus.NOT_AUTOMATED


def test_star_waiting_period_evidence_refs_are_deduplicated() -> None:
    waiting = _concept(STAR_COMPREHENSIVE_COVERAGE, "waiting_periods")

    assert len(waiting.evidence_reference_ids) == len(set(waiting.evidence_reference_ids))
