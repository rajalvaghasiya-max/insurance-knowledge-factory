from __future__ import annotations

import json
from pathlib import Path

from insurance_intelligence.authoritative_publication.materializer import (
    build_authoritative_publication_materialization_request,
    materialize_authoritative_published_evidence,
)
from insurance_intelligence.contracts.authoritative_publication import (
    build_governed_semantic_component,
)
from insurance_intelligence.contracts.publication_decision import (
    build_publication_boundary_authorization,
)
from insurance_intelligence.coverage_registry.health_seed import HEALTH_COVERAGE_REGISTRY
from insurance_intelligence.evidence.coverage_registry_source import (
    build_coverage_registry_published_source_lookup,
)
from insurance_intelligence.evidence.published_artifact_store import (
    persist_published_evidence_source,
)
from insurance_intelligence.rule_certification.waiting_period import (
    build_waiting_period_certification_case,
    run_waiting_period_certification_case,
)

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "knowledge/factory/registry_backed/star_health_star_comprehensive/publication/star_ped_publication_spec.json"


def _spec():
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _certified_source(*, drop_component_id: str | None = None):
    spec = _spec()
    case = build_waiting_period_certification_case(
        binding_spec_path=spec["binding_spec_path"],
        repository_root=ROOT,
    )
    certification = run_waiting_period_certification_case(case)
    authorization_spec = spec["boundary_authorization"]
    authorization = build_publication_boundary_authorization(
        authorization_id=authorization_spec["authorization_id"],
        governed_subject_reference=spec["governed_subject_reference"],
        certification_id=spec["certification_id"],
        resolved_boundary_tokens=tuple(authorization_spec["resolved_boundary_tokens"]),
        authorization_authority=authorization_spec["authorization_authority"],
        trace_references=tuple(authorization_spec["trace_references"]),
    )
    components = tuple(
        build_governed_semantic_component(
            component_id=item["component_id"],
            status=item["status"],
            evidence_references=tuple(item["evidence_references"]),
        )
        for item in spec["semantic_components"]
        if item["component_id"] != drop_component_id
    )
    request = build_authoritative_publication_materialization_request(
        decision_id=spec["decision_id"],
        publication_id=spec["publication_id"],
        projection_id=spec["projection_id"],
        decision_reasons=tuple(spec["decision_reasons"]),
        decision_authority=spec["decision_authority"],
        publication_authority=spec["publication_authority"],
        limitations=tuple(spec["limitations"]),
        semantic_components=components,
        boundary_authorization=authorization,
    )
    return materialize_authoritative_published_evidence(
        certification=certification,
        certified_evidence=case.evidence_output,
        request=request,
    )


def test_star_ped_materializes_through_generic_publication_machinery_from_data_only_spec():
    source = _certified_source()

    assert source.publication.publication_status == "AUTHORITATIVE"
    assert source.publication.topic_id == "waiting_period"
    assert source.publication.authorization_id == (
        "publication-authorization:star_health_star_comprehensive_ped_wait_36_months"
    )
    assert tuple(item.component_id for item in source.publication.semantic_components) == (
        "waiting_period_duration",
        "continuity_or_credit_rule",
    )
    claims = {item.field_or_topic: item.claim for item in source.certified_evidence.evidence_packages}
    assert claims["WAITING_PERIOD_DURATION"] == "The waiting period duration is 36 MONTHS."
    assert "continuously covered without any break" in claims["CONTINUITY_OR_CREDIT_RULE"]
    assert any("customer-specific eligibility or claim payment" in item for item in source.publication.limitations)
    assert any("optional PED buy-back" in item for item in source.publication.limitations)


def test_star_ped_negative_control_removes_continuity_from_published_semantic_projection():
    full_source = _certified_source()
    perturbed_source = _certified_source(drop_component_id="continuity_or_credit_rule")

    full_ids = tuple(item.component_id for item in full_source.publication.semantic_components)
    perturbed_ids = tuple(item.component_id for item in perturbed_source.publication.semantic_components)
    assert "continuity_or_credit_rule" in full_ids
    assert "continuity_or_credit_rule" not in perturbed_ids
    assert perturbed_source.certified_evidence == full_source.certified_evidence


def test_star_ped_frozen_artifacts_are_discoverable_by_existing_generic_lookup(tmp_path):
    source = _certified_source()
    publication_dir = (
        tmp_path
        / "knowledge/factory/registry_backed/star_health_star_comprehensive/publication"
    )
    persist_published_evidence_source(
        source=source,
        publication_path=publication_dir / "ped_waiting_period_authoritative_publication.json",
        certified_evidence_path=publication_dir / "ped_waiting_period_certified_evidence.json",
    )
    lookup = build_coverage_registry_published_source_lookup(
        registry=HEALTH_COVERAGE_REGISTRY,
        repository_root=tmp_path,
    )

    class Requirement:
        evidence_category = "NORMALIZED_PRODUCT_FACT"
        subject_reference = "star_health:star_comprehensive"
        reason = "What is the PED waiting period in Star Comprehensive?"

    resolved = lookup("star_health:star_comprehensive", Requirement())
    assert resolved is not None
    assert resolved.publication.publication_id == source.publication.publication_id
    assert resolved == source
