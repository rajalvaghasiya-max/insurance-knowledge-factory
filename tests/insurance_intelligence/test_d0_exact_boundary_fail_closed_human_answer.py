from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from insurance_intelligence.authoritative_publication.governed import (
    build_governed_authoritative_publication,
)
from insurance_intelligence.contracts.full_cycle import build_orchestration_request, build_product_scope
from insurance_intelligence.entity_resolution.registry_adapter import load_runtime_registry_from_files
from insurance_intelligence.evidence.published_materialization import PublishedEvidenceSource
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
from insurance_intelligence.response.human_answer import project_human_answer
from insurance_intelligence.response.registry import ResponseFormatRegistry, build_format_definition
from insurance_intelligence.rule_certification.star_health_initial_waiting_period import (
    build_star_comprehensive_initial_waiting_period_case,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = ROOT / "knowledge/factory/registry_backed"
STAR_IDENTITY = ROOT / "docs/architecture/star_health_star_comprehensive_product_identity_reference_spec.json"
PUBLICATION_SPEC = (
    "knowledge/factory/registry_backed/star_health_star_comprehensive/publication/"
    "star_initial_waiting_period_publication_spec.json"
)


def _request():
    return build_orchestration_request(
        execution_id="d0-boundary-star-initial-waiting-period-v1",
        mode="INTELLIGENCE_RESPONSE",
        product_scope=build_product_scope(
            domain="health",
            insurer_id="star_health",
            product_id="star_comprehensive",
        ),
        question="If I claim for an illness on 2026-01-31, will the initial waiting period apply?",
        audience="CUSTOMER",
        knowledge_snapshot_id="star-initial-waiting-period-authoritative-v1",
        customer_context={
            "claim_scenario": "illness treatment on 2026-01-31 on the exact initial waiting-period boundary",
            "case_specific_applicability": True,
            "policy_start_date": "2026-01-01",
            "claim_date": "2026-01-31",
            "waiting_period_continuity_credit_status": "NOT_APPLICABLE",
            "waiting_period_exception_status": "NOT_APPLICABLE",
        },
        allow_llm_rendering=False,
    )


def _dependencies(request):
    registry = load_runtime_registry_from_files((STAR_IDENTITY,))
    publication = build_governed_authoritative_publication(
        publication_spec_path=PUBLICATION_SPEC,
        repository_root=ROOT,
    )
    certified_case = build_star_comprehensive_initial_waiting_period_case()
    source = PublishedEvidenceSource(
        publication=publication,
        certified_evidence=certified_case.evidence_output,
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
            selection_record_ref=PUBLICATION_SPEC,
        )

    def source_lookup(entity_reference: str, requirement):
        text = " ".join(
            str(getattr(requirement, field, ""))
            for field in ("evidence_category", "subject_reference", "reason")
        ).casefold()
        if entity_reference != "star_health:star_comprehensive":
            return None
        if "waiting" not in text and "claim" not in text:
            return None
        return source

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


def test_d0_exact_boundary_fails_closed_with_human_next_step() -> None:
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

    reasoning = dependencies.store.get(f"{request.execution_id}:real:reasoning")
    assert not reasoning.findings
    assert reasoning.reasoning_status in {"NOT_REASONED", "PARTIALLY_REASONED"}

    response = dependencies.store.get(f"{request.execution_id}:real:response_assembly")
    projection = project_human_answer(response)
    answer_text = projection.human_view.answer.casefold()
    unknown_text = " ".join(projection.human_view.unknowns).casefold()

    assert projection.human_view.unknowns
    assert projection.human_view.next_step
    assert "boundary" in unknown_text or "cannot" in unknown_text or "uncertain" in unknown_text
    assert "still active" not in answer_text
    assert "waiting period is complete" not in answer_text
    assert "claim approval" not in answer_text
    assert "claim payment" not in answer_text
    assert projection.provenance_panel.evidence_references
    assert projection.provenance_panel.response_trace
