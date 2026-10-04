from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from insurance_intelligence.contracts.full_cycle import build_orchestration_request, build_product_scope
from insurance_intelligence.coverage_registry.health_seed import HEALTH_COVERAGE_REGISTRY
from insurance_intelligence.entity_resolution.registry_adapter import load_runtime_registry_from_files
from insurance_intelligence.evidence.coverage_registry_source import build_coverage_registry_published_source_lookup
from insurance_intelligence.evidence.published_resolver import PublishedEvidenceResolver
from insurance_intelligence.orchestration.execution_state import RuntimeStageObjectStore
from insurance_intelligence.orchestration.intelligence_adapters import execute_intelligence_stage
from insurance_intelligence.orchestration.product_instance_binding import ProductIdentityRecordEvidence
from insurance_intelligence.orchestration.real_response_prefix import RealResponsePrefixDependencies, build_real_response_prefix_adapters
from insurance_intelligence.terminology.concept_resolver import CanonicalConceptResolver
from insurance_intelligence.terminology.health_seed import build_health_concept_registry_v1


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = ROOT / "knowledge/factory/registry_backed"
STAR_IDENTITY = ROOT / "docs/architecture/star_health_star_comprehensive_product_identity_reference_spec.json"

QUESTIONS = (
    "How does restoration work in Star Comprehensive?",
    "When does the restored sum insured become available?",
    "Can I use the restored amount for the same illness?",
    "Can I use restoration in the same hospitalization?",
)


def _request(question: str, execution_id: str):
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
        knowledge_snapshot_id="health-repeatability-concept4-restoration-v1",
        allow_llm_rendering=False,
    )


def _dependencies(execution_id: str):
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
        # Deliberately fail closed: concept #4 has registered primary source and
        # governed restoration shape, but no canonical authoritative publication.
        return None

    return RealResponsePrefixDependencies(
        store=RuntimeStageObjectStore(execution_id=execution_id),
        product_registry=registry,
        identity_record_lookup=identity_lookup,
        knowledge_snapshot_lookup=snapshot_lookup,
        published_evidence_resolver=PublishedEvidenceResolver(source_lookup),
        repository_roots=(str(REGISTRY_ROOT),),
        concept_resolver=CanonicalConceptResolver(build_health_concept_registry_v1()),
    )


def _assert_missing_publication_fails_closed(question: str, execution_id: str) -> None:
    request = _request(question, execution_id)
    adapters = build_real_response_prefix_adapters(dependencies=_dependencies(execution_id))

    prior = (request.knowledge_snapshot_id,)
    observed = []
    for sequence, adapter in enumerate(adapters, start=1):
        result = execute_intelligence_stage(
            request=request,
            adapter=adapter,
            sequence=sequence,
            input_ids=prior,
        )
        observed.append(result)
        if result.status not in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"}:
            break
        prior = tuple(item.output_id for item in result.outputs)

    failed = observed[-1]
    assert failed.stage == "CERTIFIED_KNOWLEDGE_RETRIEVAL"
    assert failed.status == "FAILED"
    assert failed.failure is not None
    assert (
        failed.failure.message
        == "certified knowledge snapshot was not admitted by governed lookup"
    )


def test_q1_restoration_explanation_fails_closed_without_authoritative_publication():
    _assert_missing_publication_fails_closed(QUESTIONS[0], "health-repeatability-concept4-q1")


def test_q2_restoration_trigger_fails_closed_without_authoritative_publication():
    _assert_missing_publication_fails_closed(QUESTIONS[1], "health-repeatability-concept4-q2")


def test_q3_same_illness_fails_closed_without_authoritative_publication():
    _assert_missing_publication_fails_closed(QUESTIONS[2], "health-repeatability-concept4-q3")


def test_q4_same_hospitalization_fails_closed_without_authoritative_publication():
    _assert_missing_publication_fails_closed(QUESTIONS[3], "health-repeatability-concept4-q4")
