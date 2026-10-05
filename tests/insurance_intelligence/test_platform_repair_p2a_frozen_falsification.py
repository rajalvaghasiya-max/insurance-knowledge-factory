# Falsification-only: preserve the five frozen downstream cases unchanged after P2A.
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
from insurance_intelligence.orchestration.real_response_assembly import build_real_response_assembly_adapters
from insurance_intelligence.orchestration.real_response_prefix import CertifiedKnowledgeSelection, RealResponsePrefixDependencies
from insurance_intelligence.response.human_answer import project_human_answer
from insurance_intelligence.response.registry import ResponseFormatRegistry, build_format_definition
from insurance_intelligence.terminology.concept_resolver import CanonicalConceptResolver
from insurance_intelligence.terminology.health_seed import build_health_concept_registry_v1

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = ROOT / "knowledge/factory/registry_backed"
STAR_IDENTITY = ROOT / "docs/architecture/star_health_star_comprehensive_product_identity_reference_spec.json"
BARIATRIC_PUBLICATION = ROOT / "knowledge/factory/registry_backed/star_health_star_comprehensive/publication/bariatric_surgery_authoritative_publication.json"
ROOM_RENT_PUBLICATION = ROOT / "knowledge/factory/registry_backed/star_health_star_comprehensive/publication/room_rent_authoritative_publication.json"


def _styles():
    return ExplanationStyleRegistry((build_style_definition(style_id="customer-simple-plain-language-v1", style_version="1.0", audience="CUSTOMER", reading_level="SIMPLE", explanation_modes=("PLAIN_LANGUAGE",)),))


def _responses():
    return ResponseFormatRegistry((build_format_definition(format_id="customer-standard-p2a-falsification-v1", format_version="1.0", response_format="STANDARD", audiences=("CUSTOMER",), response_statuses=("ANSWER", "ANSWER_WITH_LIMITATIONS"), section_order=("DIRECT_ANSWER", "CUSTOMER_EXPLANATION", "CUSTOMER_QUALIFICATION", "NEXT_STEP", "EXPLANATION", "CONDITION", "LIMITATION", "EVIDENCE"), allowed_section_types=("DIRECT_ANSWER", "CUSTOMER_EXPLANATION", "CUSTOMER_QUALIFICATION", "NEXT_STEP", "EXPLANATION", "CONDITION", "LIMITATION", "EVIDENCE"), direct_answer_policy="REQUIRED", evidence_policy="WHEN_AVAILABLE", limitation_policy="REQUIRED_WHEN_PRESENT", assumption_policy="WHEN_PRESENT", clarification_policy="FORBIDDEN", max_sections=12),))


def _run(question: str, *, execution_id: str, publication: Path):
    request = build_orchestration_request(execution_id=execution_id, mode="INTELLIGENCE_RESPONSE", product_scope=build_product_scope(domain="health", insurer_id="star_health", product_id="star_comprehensive"), question=question, audience="CUSTOMER", knowledge_snapshot_id="platform-repair-p2a-frozen-falsification-v1", allow_llm_rendering=False)
    registry = load_runtime_registry_from_files((STAR_IDENTITY,))
    source_lookup = build_coverage_registry_published_source_lookup(registry=HEALTH_COVERAGE_REGISTRY, repository_root=ROOT)

    def identity_lookup(entity_id: str):
        if entity_id != "star_health:star_comprehensive":
            return None
        return ProductIdentityRecordEvidence(canonical_entity_id=entity_id, identity_record_ref=STAR_IDENTITY.relative_to(ROOT).as_posix(), identity_record_hash=sha256(STAR_IDENTITY.read_bytes()).hexdigest())

    def snapshot_lookup(snapshot_id, product_scope):
        if snapshot_id != request.knowledge_snapshot_id:
            return None
        if f"{product_scope.insurer_id}:{product_scope.product_id}" != "star_health:star_comprehensive":
            return None
        return CertifiedKnowledgeSelection(snapshot_id=snapshot_id, canonical_entity_id="star_health:star_comprehensive", selection_record_ref=publication.relative_to(ROOT).as_posix())

    dependencies = RealResponsePrefixDependencies(store=RuntimeStageObjectStore(execution_id=request.execution_id), product_registry=registry, identity_record_lookup=identity_lookup, knowledge_snapshot_lookup=snapshot_lookup, published_evidence_resolver=PublishedEvidenceResolver(source_lookup), repository_roots=(str(REGISTRY_ROOT),), concept_resolver=CanonicalConceptResolver(build_health_concept_registry_v1()))
    adapters = build_real_response_assembly_adapters(dependencies=dependencies, style_registry=_styles(), response_registry=_responses())
    prior = (request.knowledge_snapshot_id,)
    for sequence, adapter in enumerate(adapters, start=1):
        result = execute_intelligence_stage(request=request, adapter=adapter, sequence=sequence, input_ids=prior)
        assert result.status in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"}, (result.stage, result.failure.message if result.failure else result.limitations)
        prior = tuple(item.output_id for item in result.outputs)
    response = dependencies.store.get(f"{request.execution_id}:real:response_assembly")
    return project_human_answer(response)


def test_bariatric_q2_reaches_customer_answer_path_after_p2a():
    projection = _run("What conditions must I meet for bariatric surgery under Star Comprehensive?", execution_id="p2a-frozen-bariatric-q2", publication=BARIATRIC_PUBLICATION)
    assert projection.human_view.answer


def test_room_rent_q1_reaches_customer_answer_path_after_p2a():
    projection = _run("What room am I eligible for in Star Comprehensive?", execution_id="p2a-frozen-room-q1", publication=ROOM_RENT_PUBLICATION)
    assert projection.human_view.answer


def test_room_rent_q2_reaches_customer_answer_path_after_p2a():
    projection = _run("Does Star Comprehensive have a room rent limit?", execution_id="p2a-frozen-room-q2", publication=ROOM_RENT_PUBLICATION)
    assert projection.human_view.answer


def test_room_rent_q3_reaches_customer_answer_path_after_p2a():
    projection = _run("What happens if I choose a room above the permitted category?", execution_id="p2a-frozen-room-q3", publication=ROOM_RENT_PUBLICATION)
    assert projection.human_view.answer


def test_room_rent_q4_reaches_customer_answer_path_after_p2a():
    projection = _run("If I take a deluxe room, will my whole claim be reduced?", execution_id="p2a-frozen-room-q4", publication=ROOM_RENT_PUBLICATION)
    assert projection.human_view.answer
