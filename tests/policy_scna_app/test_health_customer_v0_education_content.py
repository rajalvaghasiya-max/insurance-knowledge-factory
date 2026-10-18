from __future__ import annotations

from pathlib import Path

from insurance_intelligence.education_publication.repository import EducationPublicationRepository
from scripts.score_gsi_p1_frozen_gate import SOFT_LEAK_PHRASES


PUBLICATION_ROOT = Path("knowledge/factory/education_publications")
EXPECTED_CONCEPTS = {
    "pre_existing_disease",
    "waiting_period",
    "restoration",
    "room_rent_limit",
    "bariatric_surgery",
    "conditional_copayment",
}


def _repository() -> EducationPublicationRepository:
    return EducationPublicationRepository.from_json_files(
        sorted(PUBLICATION_ROOT.glob("*_education_publication.json"))
    )


def _customer_text(publication) -> str:
    parts = [
        publication.plain_language_explanation,
        publication.practical_implication,
        *publication.limitations,
        publication.product_specific_boundary,
        publication.customer_document_boundary,
    ]
    for example in publication.examples:
        parts.extend((example.scenario, example.result, example.boundary))
    return " ".join(parts).lower()


def test_seed_concept_education_repository_is_complete_for_v0() -> None:
    repository = _repository()

    for concept_id in EXPECTED_CONCEPTS:
        publication = repository.get_by_concept(concept_id)
        assert publication is not None, concept_id
        assert publication.allowed_uses == ("CUSTOMER_EDUCATION",)
        assert publication.examples
        assert publication.plain_language_explanation.strip()
        assert publication.practical_implication.strip()
        assert publication.product_specific_boundary.strip()


def test_seed_education_avoids_frozen_authority_leak_phrases() -> None:
    repository = _repository()

    for concept_id in EXPECTED_CONCEPTS:
        publication = repository.get_by_concept(concept_id)
        assert publication is not None
        text = _customer_text(publication)
        hits = [phrase for phrase in SOFT_LEAK_PHRASES if phrase in text]
        assert hits == [], (concept_id, hits)


def test_each_new_concept_keeps_product_specific_dependencies_explicit() -> None:
    repository = _repository()

    for concept_id in EXPECTED_CONCEPTS - {"pre_existing_disease"}:
        publication = repository.get_by_concept(concept_id)
        assert publication is not None
        combined = " ".join(
            (
                publication.practical_implication,
                publication.product_specific_boundary,
                *publication.limitations,
            )
        ).lower()
        assert "product" in combined or "policy" in combined
        assert "claim" in combined
