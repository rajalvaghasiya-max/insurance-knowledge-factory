from __future__ import annotations

import json
from pathlib import Path

import pytest

from insurance_intelligence.contracts.full_cycle import (
    build_orchestration_request,
    build_product_scope,
)
from insurance_intelligence.contracts.intent import build_input as build_intent_input
from insurance_intelligence.education_publication.repository import (
    EducationPublicationRepository,
    EducationPublicationRepositoryError,
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


def _request(question: str):
    return build_orchestration_request(
        execution_id="d0-education-publication-lookup",
        mode="INTELLIGENCE_RESPONSE",
        product_scope=build_product_scope(
            domain="health",
            insurer_id="star_health",
            product_id="star_comprehensive",
        ),
        question=question,
        audience="CUSTOMER",
        knowledge_snapshot_id="d0-education-publication-lookup-v1",
        allow_llm_rendering=False,
    )


def _intent(request):
    return IntentAnalyzer().analyze(
        build_intent_input(
            request_id=request.execution_id,
            text=request.question or "",
            domain_hint="health",
        )
    )


def _lookup(repository: EducationPublicationRepository):
    return GovernedEducationPublicationLookup(
        repository=repository,
        concept_resolver=CanonicalConceptResolver(
            build_health_concept_registry_v1()
        ),
    )


def test_case_a_selects_only_available_governed_ped_education_publication() -> None:
    request = _request("What is the PED waiting period in Star Comprehensive?")
    repository = EducationPublicationRepository.from_json_files((PED_PUBLICATION,))

    publications = tuple(_lookup(repository)(request, _intent(request)))

    assert tuple(item.publication_id for item in publications) == (
        "education_pre_existing_disease_v1",
    )
    assert tuple(item.concept_id for item in publications) == (
        "pre_existing_disease",
    )


def test_missing_waiting_period_education_is_a_safe_noop() -> None:
    request = _request("What is the waiting period in Star Comprehensive?")
    repository = EducationPublicationRepository.from_json_files((PED_PUBLICATION,))

    assert tuple(_lookup(repository)(request, _intent(request))) == ()


def test_unknown_or_near_concept_language_is_a_safe_noop() -> None:
    request = _request("What is the waiting-ish period for an old illness?")
    repository = EducationPublicationRepository.from_json_files((PED_PUBLICATION,))

    assert tuple(_lookup(repository)(request, _intent(request))) == ()


def test_duplicate_concept_publications_are_rejected(tmp_path: Path) -> None:
    raw = json.loads(PED_PUBLICATION.read_text(encoding="utf-8"))
    duplicate = dict(raw)
    duplicate["publication_id"] = "education_pre_existing_disease_duplicate_v1"
    duplicate["publication_receipt_id"] = "education_receipt_1234567890abcdef1234"

    duplicate_path = tmp_path / "duplicate.json"
    duplicate_path.write_text(json.dumps(duplicate), encoding="utf-8")

    with pytest.raises(
        EducationPublicationRepositoryError,
        match="duplicate education publication for concept_id",
    ):
        EducationPublicationRepository.from_json_files(
            (PED_PUBLICATION, duplicate_path)
        )


def test_malformed_publication_json_is_rejected(tmp_path: Path) -> None:
    raw = json.loads(PED_PUBLICATION.read_text(encoding="utf-8"))
    raw.pop("publication_receipt_id")

    path = tmp_path / "malformed.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(
        EducationPublicationRepositoryError,
        match="fields mismatch",
    ):
        EducationPublicationRepository.from_json_files((path,))
