from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from insurance_intelligence.contracts.full_cycle import (
    build_orchestration_request,
    build_product_scope,
)
from insurance_intelligence.coverage_registry.health_seed import HEALTH_COVERAGE_REGISTRY
from insurance_intelligence.entity_resolution.registry_adapter import load_runtime_registry_from_files
from insurance_intelligence.evidence.coverage_registry_source import (
    build_coverage_registry_published_source_lookup,
)
from insurance_intelligence.evidence.published_resolver import PublishedEvidenceResolver
from insurance_intelligence.orchestration.execution_state import RuntimeStageObjectStore
from insurance_intelligence.orchestration.intelligence_adapters import execute_intelligence_stage
from insurance_intelligence.orchestration.product_instance_binding import ProductIdentityRecordEvidence
from insurance_intelligence.orchestration.real_response_prefix import (
    CertifiedKnowledgeSelection,
    RealResponsePrefixDependencies,
)
from insurance_intelligence.orchestration.real_response_reasoning import (
    build_real_response_reasoning_adapters,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = ROOT / "knowledge/factory/registry_backed"
STAR_IDENTITY = ROOT / "docs/architecture/star_health_star_comprehensive_product_identity_reference_spec.json"
STAR_PED_PUBLICATION = (
    ROOT
    / "knowledge/factory/registry_backed/star_health_star_comprehensive/publication"
    / "ped_waiting_period_authoritative_publication.json"
)


def _request(question: str, *, execution_id: str):
    return build_orchestration_request(
        execution_id=execution_id,
        mode="INTELLIGENCE_RESPONSE",
        product_scope=build_product_scope(
            domain="health",
            insurer_id="star_health",
            product_id="star_comprehensive",
        ),
        question=question,
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


def _run(question: str, *, execution_id: str):
    request = _request(question, execution_id=execution_id)
    dependencies = _dependencies(request)
    adapters = build_real_response_reasoning_adapters(dependencies=dependencies)
    assert tuple(adapter.stage for adapter in adapters) == request.requested_stage_order[:10]

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
        if result.status not in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"}:
            break
        prior = tuple(item.output_id for item in result.outputs)
    return request, dependencies, tuple(results)


def test_star_ped_case_b_reaches_real_reasoning_through_factual_lane_only():
    request, dependencies, results = _run(
        "What is the PED waiting period in Star Comprehensive?",
        execution_id="real-reasoning-star-ped-case-b",
    )

    assert len(results) == 10
    assert all(item.status in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"} for item in results)
    assert results[-1].stage == "REASONING"

    reasoning = dependencies.store.get(results[-1].outputs[0].output_id)
    assert reasoning.request_id == request.execution_id
    assert reasoning.reasoning_status == "REASONED"
    assert reasoning.findings
    assert {item.rule_id for item in reasoning.rule_executions} == {"direct_documented_fact_v1"}
    assert {item.rule_id for item in reasoning.findings} == {"direct_documented_fact_v1"}
    assert not any(item.rule_id.startswith("conditional_copayment_") for item in reasoning.rule_executions)


def test_product_explanation_control_remains_clarification_blocked_before_reasoning():
    _request_obj, _dependencies_obj, results = _run(
        "Explain Star Comprehensive",
        execution_id="real-reasoning-product-explanation-control",
    )

    assert results[-1].stage == "INSTANCE_SUFFICIENCY"
    assert results[-1].status == "FAILED"
    assert results[-1].failure is not None
    assert "CLARIFICATION_REQUIRED" in results[-1].failure.message
