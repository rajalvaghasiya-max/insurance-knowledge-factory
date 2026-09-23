from __future__ import annotations

from pathlib import Path

from insurance_intelligence.contracts.full_cycle import (
    build_orchestration_request,
    build_product_scope,
)
from insurance_intelligence.contracts.intent import build_input as build_intent_input
from insurance_intelligence.education_publication.repository import (
    EducationPublicationRepository,
    GovernedEducationPublicationLookup,
)
from insurance_intelligence.intent.analyzer import IntentAnalyzer
from insurance_intelligence.terminology.concept_resolver import CanonicalConceptResolver
from insurance_intelligence.terminology.health_seed import build_health_concept_registry_v1


ROOT = Path(__file__).resolve().parents[2]
PED_PUBLICATION = (
    ROOT
    / "knowledge/factory/education_publications"
    / "pre_existing_disease_education_publication.json"
)


def test_case_a_selects_only_available_governed_ped_education_publication() -> None:
    question = "What is the PED waiting period in Star Comprehensive?"
    request = build_orchestration_request(
        execution_id="case-a-education-lookup",
        mode="INTELLIGENCE_RESPONSE",
        product_scope=build_product_scope(
            domain="health",
            insurer_id="star_health",
            product_id="star_comprehensive",
        ),
        question=question,
        audience="CUSTOMER",
        knowledge_snapshot_id="case-a-education-lookup-v1",
        allow_llm_rendering=False,
    )
    intent = IntentAnalyzer().analyze(
        build_intent_input(
            request_id=request.execution_id,
            text=question,
            domain_hint="health",
        )
    )
    repository = EducationPublicationRepository.from_json_files((PED_PUBLICATION,))
    lookup = GovernedEducationPublicationLookup(
        repository=repository,
        concept_resolver=CanonicalConceptResolver(build_health_concept_registry_v1()),
    )

    publications = tuple(lookup(request, intent))

    assert tuple(item.publication_id for item in publications) == (
        "education_pre_existing_disease_v1",
    )
    assert tuple(item.concept_id for item in publications) == (
        "pre_existing_disease",
    )
