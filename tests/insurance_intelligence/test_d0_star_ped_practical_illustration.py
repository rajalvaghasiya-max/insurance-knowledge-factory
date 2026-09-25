from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from insurance_intelligence.contracts.full_cycle import (
    build_orchestration_request,
    build_product_scope,
)
from insurance_intelligence.coverage_registry.health_seed import HEALTH_COVERAGE_REGISTRY
from insurance_intelligence.education_publication.repository import (
    EducationPublicationRepository,
    GovernedEducationPublicationLookup,
    GovernedPracticalIllustrationLookup,
    PracticalIllustrationProfileRepository,
)
from insurance_intelligence.entity_resolution.registry_adapter import load_runtime_registry_from_files
from insurance_intelligence.evidence.coverage_registry_source import (
    build_coverage_registry_published_source_lookup,
)
from insurance_intelligence.evidence.published_resolver import PublishedEvidenceResolver
from insurance_intelligence.explanation.registry import (
    ExplanationStyleRegistry,
    build_style_definition,
)
from insurance_intelligence.orchestration.execution_state import RuntimeStageObjectStore
from insurance_intelligence.orchestration.intelligence_adapters import execute_intelligence_stage
from insurance_intelligence.orchestration.product_instance_binding import (
    ProductIdentityRecordEvidence,
)
from insurance_intelligence.orchestration.real_response_assembly import (
    build_real_response_assembly_adapters,
)
from insurance_intelligence.orchestration.real_response_prefix import (
    CertifiedKnowledgeSelection,
    RealResponsePrefixDependencies,
)
from insurance_intelligence.response.human_answer import project_human_answer
from insurance_intelligence.response.registry import (
    ResponseFormatRegistry,
    build_format_definition,
)
from insurance_intelligence.terminology.concept_resolver import CanonicalConceptResolver
from insurance_intelligence.terminology.health_seed import build_health_concept_registry_v1


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = ROOT / "knowledge/factory/registry_backed"
STAR_IDENTITY = ROOT / "docs/architecture/star_health_star_comprehensive_product_identity_reference_spec.json"
STAR_PED_PUBLICATION = (
    ROOT
    / "knowledge/factory/registry_backed/star_health_star_comprehensive/publication"
    / "ped_waiting_period_authoritative_publication.json"
)
PED_EDUCATION = (
    ROOT
    / "knowledge/factory/education_publications"
    / "pre_existing_disease_education_publication.json"
)
PED_ILLUSTRATION = (
    ROOT
    / "knowledge/factory/illustration_profiles"
    / "pre_existing_disease_practical_illustration_v1.json"
)


def _request():
    return build_orchestration_request(
        execution_id="d0-target-star-ped-practical-illustration",
        mode="INTELLIGENCE_RESPONSE",
        product_scope=build_product_scope(
            domain="health",
            insurer_id="star_health",
            product_id="star_comprehensive",
        ),
        question="What is the PED waiting period in Star Comprehensive?",
        audience="CUSTOMER",
        knowledge_snapshot_id="d0-target-star-ped-practical-illustration-v1",
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


def _responses():
    return ResponseFormatRegistry((
        build_format_definition(
            format_id="customer-education-practical-v1",
            format_version="1.0",
            response_format="STANDARD",
            audiences=("CUSTOMER",),
            response_statuses=("ANSWER", "ANSWER_WITH_LIMITATIONS"),
            section_order=(
                "EDUCATION",
                "DIRECT_ANSWER",
                "EXAMPLE",
                "PRACTICAL_ILLUSTRATION",
                "CUSTOMER_QUALIFICATION",
                "NEXT_STEP",
                "EXPLANATION",
                "CONDITION",
                "LIMITATION",
                "EVIDENCE",
            ),
            allowed_section_types=(
                "EDUCATION",
                "DIRECT_ANSWER",
                "EXAMPLE",
                "PRACTICAL_ILLUSTRATION",
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


def _lookups():
    resolver = CanonicalConceptResolver(build_health_concept_registry_v1())
    education = GovernedEducationPublicationLookup(
        repository=EducationPublicationRepository.from_json_files((PED_EDUCATION,)),
        concept_resolver=resolver,
    )
    illustrations = GovernedPracticalIllustrationLookup(
        repository=PracticalIllustrationProfileRepository.from_json_files(
            (PED_ILLUSTRATION,)
        ),
        concept_resolver=resolver,
    )
    return education, illustrations


def _run():
    request = _request()
    dependencies = _dependencies(request)
    education_lookup, illustration_lookup = _lookups()
    adapters = build_real_response_assembly_adapters(
        dependencies=dependencies,
        style_registry=_styles(),
        response_registry=_responses(),
        education_publication_lookup=education_lookup,
        practical_illustration_profile_lookup=illustration_lookup,
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

    response = dependencies.store.get(
        f"{request.execution_id}:real:response_assembly"
    )
    explanation = dependencies.store.get(
        f"{request.execution_id}:real:explanation_authority_enforced"
    )
    return response, explanation


def test_case_a_real_path_composes_founder_approved_practical_illustration() -> None:
    response, explanation = _run()

    assert response.direct_answer == "The waiting period duration is 36 MONTHS."

    included = tuple(section for section in response.sections if section.status == "INCLUDED")
    assert any(section.section_type == "EDUCATION" for section in included)
    practical = tuple(
        section for section in included
        if section.section_type == "PRACTICAL_ILLUSTRATION"
    )
    assert len(practical) == 1

    section = practical[0]
    text = section.text.lower()
    assert "ear condition" in text
    assert "dengue" in text
    assert "10 months" in text
    assert "40 months" in text
    assert "36-month" in text
    assert "does not by itself block" in text
    assert "no longer applies on that basis" in text
    assert "will pay" not in text
    assert "fully covered" not in text

    assert section.education_publication_ids == (
        "education_pre_existing_disease_v1",
    )
    assert section.approved_finding_ids
    assert section.evidence_reference_ids

    fidelity = {
        item.check_type: item.status
        for item in explanation.fidelity_checks
    }
    assert fidelity["PRACTICAL_ILLUSTRATION_FIDELITY"] == "PASSED"


def test_founder_profile_is_loaded_only_as_reviewed_governed_data() -> None:
    repository = PracticalIllustrationProfileRepository.from_json_files(
        (PED_ILLUSTRATION,)
    )
    profile = repository.get_by_concept("pre_existing_disease")

    assert profile is not None
    assert profile.before_probe_value == 10
    assert profile.after_probe_value == 40
    assert profile.related_condition == "ear condition"
    assert profile.unrelated_condition == "dengue"



def test_case_a_human_projection_exposes_governed_practical_illustration() -> None:
    response, _ = _run()
    projection = project_human_answer(response)

    meaning = " ".join(projection.human_view.meaning).lower()
    assert "ear condition" in meaning
    assert "dengue" in meaning
    assert "10 months" in meaning
    assert "40 months" in meaning



def test_case_a_human_projection_separates_customer_qualifications_from_diagnostics() -> None:
    response, _ = _run()
    projection = project_human_answer(response)

    unknowns = " ".join(projection.human_view.unknowns).lower()
    assert "continuous health insurance" in unknowns
    assert "portability" in unknowns
    assert "certification applies only" not in unknowns
    assert "certification does not determine" not in unknowns
    assert "communicate only within" not in unknowns
    assert "bound_not_published" not in unknowns

    assert projection.human_view.next_step is not None
    next_step = projection.human_view.next_step.lower()
    assert "continuous health insurance" in next_step
    assert "insurer or advisor before relying" not in next_step

    diagnostics = " ".join(
        projection.provenance_panel.diagnostic_limitations
    ).lower()
    assert "certification" in diagnostics or "documented scope" in diagnostics
