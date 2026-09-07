from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from insurance_intelligence.contracts.full_cycle import build_orchestration_request, build_product_scope
from insurance_intelligence.coverage_registry.health_seed import HEALTH_COVERAGE_REGISTRY
from insurance_intelligence.entity_resolution.registry_adapter import load_runtime_registry_from_files
from insurance_intelligence.evidence.coverage_registry_source import build_coverage_registry_published_source_lookup
from insurance_intelligence.evidence.published_resolver import PublishedEvidenceResolver
from insurance_intelligence.explanation.registry import ExplanationStyleRegistry, build_style_definition
from insurance_intelligence.orchestration.execution_state import RuntimeStageObjectStore
from insurance_intelligence.orchestration.intelligence_adapters import execute_intelligence_stage
from insurance_intelligence.orchestration.product_instance_binding import ProductIdentityRecordEvidence
from insurance_intelligence.orchestration.real_response_explanation import (
    build_real_response_explanation_adapters,
)
from insurance_intelligence.orchestration.real_response_prefix import (
    CertifiedKnowledgeSelection,
    RealResponsePrefixDependencies,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = ROOT / "knowledge/factory/registry_backed"
STAR_IDENTITY = ROOT / "docs/architecture/star_health_star_comprehensive_product_identity_reference_spec.json"
STAR_PED_PUBLICATION = (
    ROOT
    / "knowledge/factory/registry_backed/star_health_star_comprehensive/publication"
    / "ped_waiting_period_authoritative_publication.json"
)


def _request():
    return build_orchestration_request(
        execution_id="real-explanation-star-ped-case-b",
        mode="INTELLIGENCE_RESPONSE",
        product_scope=build_product_scope(
            domain="health",
            insurer_id="star_health",
            product_id="star_comprehensive",
        ),
        question="What is the PED waiting period in Star Comprehensive?",
        audience="CUSTOMER",
        knowledge_snapshot_id="star-ped-answer-admissible-v1",
        allow_llm_rendering=False,
    )


def _dependencies(request):
    registry = load_runtime_registry_from_files((STAR_IDENTITY,))
    source_lookup = build_coverage_registry_published_source_lookup(
        registry=HEALTH_COVERAGE_REGISTRY,
        repository_root=ROOT,
    )

    def identity_lookup(entity_id: str):
        if entity_id != "star_health:star_comprehensive":
            return None
        return ProductIdentityRecordEvidence(
            canonical_entity_id=entity_id,
            identity_record_ref=STAR_IDENTITY.relative_to(ROOT).as_posix(),
            identity_record_hash=sha256(STAR_IDENTITY.read_bytes()).hexdigest(),
        )

    def snapshot_lookup(snapshot_id, product_scope):
        if snapshot_id != request.knowledge_snapshot_id:
            return None
        if f"{product_scope.insurer_id}:{product_scope.product_id}" != "star_health:star_comprehensive":
            return None
        if not STAR_PED_PUBLICATION.is_file():
            return None
        return CertifiedKnowledgeSelection(
            snapshot_id=snapshot_id,
            canonical_entity_id="star_health:star_comprehensive",
            selection_record_ref=STAR_PED_PUBLICATION.relative_to(ROOT).as_posix(),
        )

    return RealResponsePrefixDependencies(
        store=RuntimeStageObjectStore(execution_id=request.execution_id),
        product_registry=registry,
        identity_record_lookup=identity_lookup,
        knowledge_snapshot_lookup=snapshot_lookup,
        published_evidence_resolver=PublishedEvidenceResolver(source_lookup),
        repository_roots=(str(REGISTRY_ROOT),),
    )


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


def test_star_ped_factual_lane_reaches_authority_enforced_explanation_with_lineage_preserved():
    request = _request()
    dependencies = _dependencies(request)
    adapters = build_real_response_explanation_adapters(
        dependencies=dependencies,
        style_registry=_styles(),
    )
    assert tuple(adapter.stage for adapter in adapters) == request.requested_stage_order[:12]

    prior = (request.knowledge_snapshot_id,)
    results = []
    for sequence, adapter in enumerate(adapters, start=1):
        result = execute_intelligence_stage(
            request=request,
            adapter=adapter,
            sequence=sequence,
            input_ids=prior,
        )
        results.append(result)
        assert result.status in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"}, (
            result.stage,
            result.failure.message if result.failure else result.limitations,
        )
        prior = tuple(item.output_id for item in result.outputs)

    assert results[-1].stage == "EXPLANATION_AUTHORITY_ENFORCED"
    explanation = dependencies.store.get(results[-1].outputs[0].output_id)
    assert explanation.explanation_status in {"DRAFTED", "DRAFTED_WITH_LIMITATIONS"}
    assert explanation.fidelity_status in {"VERIFIED", "VERIFIED_WITH_LIMITATIONS"}
    drafted = tuple(section for section in explanation.sections if section.status == "DRAFTED")
    assert drafted
    assert any(section.section_type == "DIRECT_ANSWER" for section in drafted)

    decision = dependencies.store.get(
        f"{request.execution_id}:real:decision_gate_authority_enforced"
    )
    approved_evidence = set(decision.decision_output.response_packet.approved_evidence_ids)
    explanation_evidence = {
        evidence_id for section in drafted for evidence_id in section.evidence_ids
    }
    assert approved_evidence <= explanation_evidence
    assert decision.recommendation_authorized is False

    reasoning = dependencies.store.get(f"{request.execution_id}:real:reasoning")
    assert {item.rule_id for item in reasoning.rule_executions} == {"direct_documented_fact_v1"}
    assert not any(item.rule_id.startswith("conditional_copayment_") for item in reasoning.rule_executions)
