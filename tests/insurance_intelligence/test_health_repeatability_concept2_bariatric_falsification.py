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


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = ROOT / "knowledge/factory/registry_backed"
STAR_IDENTITY = ROOT / "docs/architecture/star_health_star_comprehensive_product_identity_reference_spec.json"
BARIATRIC_PUBLICATION = (
    ROOT
    / "knowledge/factory/registry_backed/star_health_star_comprehensive/publication"
    / "bariatric_surgery_authoritative_publication.json"
)


def _request():
    return build_orchestration_request(
        execution_id="health-repeatability-concept2-bariatric-falsification",
        mode="INTELLIGENCE_RESPONSE",
        product_scope=build_product_scope(
            domain="health",
            insurer_id="star_health",
            product_id="star_comprehensive",
        ),
        question="Does Star Comprehensive cover bariatric surgery?",
        audience="CUSTOMER",
        knowledge_snapshot_id="health-repeatability-concept2-bariatric-v1",
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
        return CertifiedKnowledgeSelection(
            snapshot_id=snapshot_id,
            canonical_entity_id="star_health:star_comprehensive",
            selection_record_ref=BARIATRIC_PUBLICATION.relative_to(ROOT).as_posix(),
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


def _responses():
    return ResponseFormatRegistry((
        build_format_definition(
            format_id="customer-standard-bariatric-v1",
            format_version="1.0",
            response_format="STANDARD",
            audiences=("CUSTOMER",),
            response_statuses=("ANSWER", "ANSWER_WITH_LIMITATIONS"),
            section_order=(
                "DIRECT_ANSWER",
                "CUSTOMER_EXPLANATION",
                "CUSTOMER_QUALIFICATION",
                "NEXT_STEP",
                "EXPLANATION",
                "CONDITION",
                "LIMITATION",
                "EVIDENCE",
            ),
            allowed_section_types=(
                "DIRECT_ANSWER",
                "CUSTOMER_EXPLANATION",
                "CUSTOMER_QUALIFICATION",
                "NEXT_STEP",
                "EXPLANATION",
                "CONDITION",
                "LIMITATION",
                "EVIDENCE",
            ),
            direct_answer_policy="REQUIRED",
            evidence_policy="WHEN_AVAILABLE",
            limitation_policy="REQUIRED_WHEN_PRESENT",
            assumption_policy="WHEN_PRESENT",
            clarification_policy="FORBIDDEN",
            max_sections=12,
        ),
    ))


def _run():
    request = _request()
    dependencies = _dependencies(request)
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
        assert result.status in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"}, (
            result.stage,
            result.failure.message if result.failure else result.limitations,
        )
        prior = tuple(item.output_id for item in result.outputs)

    response = dependencies.store.get(f"{request.execution_id}:real:response_assembly")
    return project_human_answer(response)


def test_concept2_current_generic_path_is_customer_usable_without_runtime_repair():
    projection = _run()
    view = projection.human_view
    customer_text = " ".join((view.answer, *view.meaning, *view.unknowns, view.next_step or ""))
    lowered = customer_text.casefold()

    assert "bariatric" in view.answer.casefold()
    assert "above 18" in lowered
    assert "two" in lowered and "surgeon" in lowered
    assert "cashless" in lowered and "approval" in lowered
    assert "bmi" in lowered
    assert "weight-loss" in lowered or "weight loss" in lowered

    assert "eligibility_criteria" not in lowered
    assert "applicability_scope" not in lowered
    assert "eligible_consequence" not in lowered
    assert "ineligible_consequence" not in lowered
    assert "exception_condition" not in lowered

    assert "guarantee claim" not in lowered
    assert "guaranteed" not in lowered
