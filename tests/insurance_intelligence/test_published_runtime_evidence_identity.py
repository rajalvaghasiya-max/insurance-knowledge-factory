from __future__ import annotations

from pathlib import Path

from insurance_intelligence.contracts.reasoning_plan import build_evidence_requirement
from insurance_intelligence.coverage_registry.health_seed import HEALTH_COVERAGE_REGISTRY
from insurance_intelligence.evidence.coverage_registry_source import (
    build_coverage_registry_published_source_lookup,
)
from insurance_intelligence.evidence.published_materialization import (
    materialize_published_requirement,
)

ROOT = Path(__file__).resolve().parents[2]
LOOKUP = build_coverage_registry_published_source_lookup(
    registry=HEALTH_COVERAGE_REGISTRY,
    repository_root=ROOT,
)


def _requirement():
    return build_evidence_requirement(
        requirement_id="lookup-requirement",
        evidence_category="NORMALIZED_PRODUCT_FACT",
        subject_reference="star_health:star_comprehensive",
        required=True,
        authority_requirement="AUTHORITATIVE",
        version_requirement="CURRENT_APPLICABLE",
        reason="What is the PED waiting period in Star Comprehensive?",
        requested_by_step="step-1",
    )


def test_same_publication_materialized_for_two_requirements_has_disjoint_runtime_ids() -> None:
    source = LOOKUP("star_health:star_comprehensive", _requirement())
    assert source is not None

    first, first_result = materialize_published_requirement(
        source=source,
        requirement_id="evreq-1",
        subject_reference="waiting period",
    )
    second, second_result = materialize_published_requirement(
        source=source,
        requirement_id="evreq-2",
        subject_reference="waiting period",
    )

    first_ids = {item.evidence_id for item in first}
    second_ids = {item.evidence_id for item in second}
    assert first_ids
    assert second_ids
    assert first_ids.isdisjoint(second_ids)
    assert set(first_result.matched_evidence_ids) == first_ids
    assert set(second_result.matched_evidence_ids) == second_ids

    for package in (*first, *second):
        assert any(
            token.startswith("certified_evidence_id:")
            for token in package.retrieval_basis
        )
        assert all(
            package.evidence_id in attribute.evidence_references
            for attribute in package.semantic_attributes
        )
