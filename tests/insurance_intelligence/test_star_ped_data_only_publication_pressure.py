from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from insurance_intelligence.authoritative_publication.materializer import (
    build_authoritative_publication_materialization_request,
    materialize_authoritative_published_evidence,
)
from insurance_intelligence.contracts.authoritative_publication import (
    build_governed_semantic_component,
)
from insurance_intelligence.contracts.full_cycle import (
    build_orchestration_request,
    build_product_scope,
)
from insurance_intelligence.contracts.publication_decision import (
    build_publication_boundary_authorization,
)
from insurance_intelligence.coverage_registry.health_seed import HEALTH_COVERAGE_REGISTRY
from insurance_intelligence.entity_resolution.registry_adapter import load_runtime_registry_from_files
from insurance_intelligence.evidence.coverage_registry_source import (
    build_coverage_registry_published_source_lookup,
)
from insurance_intelligence.evidence.published_artifact_store import (
    persist_published_evidence_source,
)
from insurance_intelligence.evidence.published_resolver import PublishedEvidenceResolver
from insurance_intelligence.explanation.registry import ExplanationStyleRegistry, build_style_definition
from insurance_intelligence.orchestration.execution_state import RuntimeStageObjectStore
from insurance_intelligence.orchestration.intelligence_adapters import execute_intelligence_stage
from insurance_intelligence.orchestration.product_instance_binding import ProductIdentityRecordEvidence
from insurance_intelligence.orchestration.real_response_assembly import build_real_response_assembly_adapters
from insurance_intelligence.orchestration.real_response_prefix import (
    CertifiedKnowledgeSelection,
    RealResponsePrefixDependencies,
)
from insurance_intelligence.response.registry import ResponseFormatRegistry, build_format_definition
from insurance_intelligence.rule_certification.waiting_period import (
    build_waiting_period_certification_case,
    run_waiting_period_certification_case,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = ROOT / "knowledge/factory/registry_backed"
STAR_IDENTITY = ROOT / "docs/architecture/star_health_star_comprehensive_product_identity_reference_spec.json"
SPEC_PATH = ROOT / "knowledge/factory/registry_backed/star_health_star_comprehensive/publication/star_ped_publication_spec.json"
CONTINUITY_CLAIM = (
    "If the Insured Person is continuously covered without any break under applicable "
    "portability norms, the waiting period is reduced to the extent of prior coverage."
)


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


def _persist_source(*, root: Path, source) -> Path:
    publication_dir = (
        root
        / "knowledge/factory/registry_backed/star_health_star_comprehensive/publication"
    )
    publication_path = publication_dir / "ped_waiting_period_authoritative_publication.json"
    persist_published_evidence_source(
        source=source,
        publication_path=publication_path,
        certified_evidence_path=publication_dir / "ped_waiting_period_certified_evidence.json",
    )
    return publication_path


def _styles():
    return ExplanationStyleRegistry((
        build_style_definition(
            style_id="customer-simple-plain-language-v1",
            style_version="1.0",
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_modes=("PLAIN_LANGUAGE",),
        ),
    ))


def _responses():
    return ResponseFormatRegistry((
        build_format_definition(
            format_id="customer-standard-answer-v1",
            format_version="1.0",
            response_format="STANDARD",
            audiences=("CUSTOMER",),
            response_statuses=("ANSWER", "ANSWER_WITH_LIMITATIONS"),
            section_order=("DIRECT_ANSWER", "EXPLANATION", "CONDITION", "LIMITATION", "EVIDENCE"),
            allowed_section_types=("DIRECT_ANSWER", "EXPLANATION", "CONDITION", "LIMITATION", "EVIDENCE"),
            direct_answer_policy="REQUIRED",
            evidence_policy="WHEN_AVAILABLE",
            limitation_policy="REQUIRED_WHEN_PRESENT",
            assumption_policy="WHEN_PRESENT",
            clarification_policy="FORBIDDEN",
        ),
    ))


def _run_real_assembled_answer(*, publication_root: Path, execution_id: str):
    request = build_orchestration_request(
        execution_id=execution_id,
        mode="INTELLIGENCE_RESPONSE",
        product_scope=build_product_scope(
            domain="health",
            insurer_id="star_health",
            product_id="star_comprehensive",
        ),
        question="What is the PED waiting period in Star Comprehensive?",
        audience="CUSTOMER",
        knowledge_snapshot_id=f"{execution_id}:snapshot",
        allow_llm_rendering=False,
    )
    registry = load_runtime_registry_from_files((STAR_IDENTITY,))
    source_lookup = build_coverage_registry_published_source_lookup(
        registry=HEALTH_COVERAGE_REGISTRY,
        repository_root=publication_root,
    )

    def identity_lookup(entity_id: str):
        if entity_id != "star_health:star_comprehensive":
            return None
        return ProductIdentityRecordEvidence(
            canonical_entity_id=entity_id,
            identity_record_ref=STAR_IDENTITY.relative_to(ROOT).as_posix(),
            identity_record_hash=sha256(STAR_IDENTITY.read_bytes()).hexdigest(),
        )

    publication_path = (
        publication_root
        / "knowledge/factory/registry_backed/star_health_star_comprehensive/publication"
        / "ped_waiting_period_authoritative_publication.json"
    )

    def snapshot_lookup(snapshot_id, product_scope):
        if snapshot_id != request.knowledge_snapshot_id:
            return None
        if f"{product_scope.insurer_id}:{product_scope.product_id}" != "star_health:star_comprehensive":
            return None
        if not publication_path.is_file():
            return None
        return CertifiedKnowledgeSelection(
            snapshot_id=snapshot_id,
            canonical_entity_id="star_health:star_comprehensive",
            selection_record_ref=publication_path.relative_to(publication_root).as_posix(),
        )

    dependencies = RealResponsePrefixDependencies(
        store=RuntimeStageObjectStore(execution_id=request.execution_id),
        product_registry=registry,
        identity_record_lookup=identity_lookup,
        knowledge_snapshot_lookup=snapshot_lookup,
        published_evidence_resolver=PublishedEvidenceResolver(source_lookup),
        repository_roots=(str(REGISTRY_ROOT),),
    )
    adapters = build_real_response_assembly_adapters(
        dependencies=dependencies,
        style_registry=_styles(),
        response_registry=_responses(),
    )

    prior = (request.knowledge_snapshot_id,)
    for sequence, adapter in enumerate(adapters, start=1):
        result = execute_intelligence_stage(
            request=request,
            adapter=adapter,
            sequence=sequence,
            input_ids=prior,
        )
        if result.status not in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"}:
            detail = result.failure.message if result.failure else result.limitations
            pytest.fail(
                "CRITERION_6_INCONCLUSIVE_COMPLETENESS_OR_SAFETY_BLOCK: "
                f"{result.stage} returned {result.status}: {detail}"
            )
        prior = tuple(item.output_id for item in result.outputs)

    response = dependencies.store.get(
        f"{request.execution_id}:real:response_assembly"
    )
    included = tuple(section for section in response.sections if section.status == "INCLUDED")
    text = " ".join((response.direct_answer, *(section.text for section in included)))
    return response, text


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


def test_star_ped_criterion6_publication_perturbation_changes_assembled_answer(tmp_path):
    full_root = tmp_path / "full"
    perturbed_root = tmp_path / "perturbed"
    _persist_source(root=full_root, source=_certified_source())
    _persist_source(
        root=perturbed_root,
        source=_certified_source(drop_component_id="continuity_or_credit_rule"),
    )

    full_response, full_text = _run_real_assembled_answer(
        publication_root=full_root,
        execution_id="star-ped-criterion6-full",
    )
    perturbed_response, perturbed_text = _run_real_assembled_answer(
        publication_root=perturbed_root,
        execution_id="star-ped-criterion6-perturbed",
    )

    assert full_response.response_status in {"ANSWER", "ANSWER_WITH_LIMITATIONS"}
    assert perturbed_response.response_status in {"ANSWER", "ANSWER_WITH_LIMITATIONS"}
    assert "36" in full_text
    assert "36" in perturbed_text
    assert CONTINUITY_CLAIM in full_text
    assert CONTINUITY_CLAIM not in perturbed_text
    assert "12" not in full_text
    assert "12" not in perturbed_text


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
