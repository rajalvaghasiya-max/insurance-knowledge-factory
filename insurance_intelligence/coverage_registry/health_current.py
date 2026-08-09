"""Current governed Health coverage registry after MO-028B promotions.

This module layers milestone-specific promotions over the immutable MO-028A seed.
Closed milestone seed records remain unchanged so historical certification retains
its original meaning.
"""
from __future__ import annotations

from dataclasses import replace

from insurance_intelligence.benefits.star_comprehensive_waiting_periods import (
    STAR_COMPREHENSIVE_WAITING_PERIOD_PUBLICATION,
)
from insurance_intelligence.coverage_registry.contracts import (
    ConceptCoverageRecord,
    ConceptCoverageStatus,
    InsuranceIntelligenceCoverageRegistry,
)
from insurance_intelligence.coverage_registry.health_seed import (
    ACTIV_ONE_NXT_COVERAGE as MO028A_ACTIV_ONE_NXT_COVERAGE,
    STAR_COMPREHENSIVE_COVERAGE as MO028A_STAR_COMPREHENSIVE_COVERAGE,
)


def _waiting_period_evidence_reference_ids() -> tuple[str, ...]:
    refs: list[str] = []
    for mechanic in STAR_COMPREHENSIVE_WAITING_PERIOD_PUBLICATION.mechanics:
        refs.extend(mechanic.evidence_reference_ids)
        for modification in mechanic.modifications:
            refs.extend(modification.evidence_reference_ids)
    return tuple(dict.fromkeys(refs))


def _promote_star_waiting_periods() -> tuple[ConceptCoverageRecord, ...]:
    promoted = []
    for concept in MO028A_STAR_COMPREHENSIVE_COVERAGE.concepts:
        if concept.concept_id != "waiting_periods":
            promoted.append(concept)
            continue
        promoted.append(
            ConceptCoverageRecord(
                concept_id="waiting_periods",
                status=ConceptCoverageStatus.CERTIFIED,
                evidence_reference_ids=_waiting_period_evidence_reference_ids(),
                comparison_ready=True,
                decision_support_ready=False,
                limitations=(
                    "A governed waiting-period assessment policy has not yet been certified for decision-support alignment.",
                    "Optional waiting-period modifications such as Buy Back are outside this base publication and require separate governed coverage.",
                ),
            )
        )
    return tuple(promoted)


STAR_COMPREHENSIVE_COVERAGE = replace(
    MO028A_STAR_COMPREHENSIVE_COVERAGE,
    concepts=_promote_star_waiting_periods(),
)

ACTIV_ONE_NXT_COVERAGE = MO028A_ACTIV_ONE_NXT_COVERAGE

HEALTH_COVERAGE_REGISTRY = InsuranceIntelligenceCoverageRegistry(
    (
        STAR_COMPREHENSIVE_COVERAGE,
        ACTIV_ONE_NXT_COVERAGE,
    )
)


__all__ = [
    "ACTIV_ONE_NXT_COVERAGE",
    "HEALTH_COVERAGE_REGISTRY",
    "STAR_COMPREHENSIVE_COVERAGE",
]
