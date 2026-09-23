from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from insurance_intelligence.contracts.education_publication import (
    build_education_publication_input,
)
from insurance_intelligence.education_publication.gate import (
    create_education_publication,
)
from knowledge_domains.health.concept_knowledge.governed_concept_to_meaning_asset import (
    GovernedConceptToMeaningAssetAdapter,
)
from knowledge_domains.health.concept_knowledge.governed_generic_concept_record import (
    GovernedGenericConceptRecordContract,
)


ROOT = Path(__file__).resolve().parents[2]
RECORD_PATH = (
    ROOT
    / "knowledge/factory/generic_concepts/pre_existing_disease"
    / "governed_generic_concept_record_v0_2.json"
)
ASSET_PATH = (
    ROOT
    / "knowledge/factory/meaning_assets"
    / "pre_existing_disease_governed_meaning_asset.json"
)
PUBLICATION_PATH = (
    ROOT
    / "knowledge/factory/education_publications"
    / "pre_existing_disease_education_publication.json"
)


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_founder_reviewed_ped_education_artifacts_regenerate_deterministically() -> None:
    record = _json(RECORD_PATH)
    committed_asset = _json(ASSET_PATH)
    committed_publication = _json(PUBLICATION_PATH)

    GovernedGenericConceptRecordContract.validate_record(record)

    regenerated_asset = GovernedConceptToMeaningAssetAdapter.build(record)
    assert regenerated_asset == committed_asset

    publication_input = build_education_publication_input(
        publication_id="education_pre_existing_disease_v1",
        meaning_asset=regenerated_asset,
        publication_authority="PolicyScna education publication authority",
    )
    regenerated_publication = create_education_publication(publication_input)

    regenerated_json = json.loads(json.dumps(asdict(regenerated_publication)))
    assert regenerated_json == committed_publication
    assert regenerated_publication.publication_receipt_id == (
        "education_receipt_99c6b5b021b97f71193d"
    )


def test_ped_education_preserves_founder_plain_language_and_safe_boundary() -> None:
    publication = _json(PUBLICATION_PATH)

    plain = publication["plain_language_explanation"]
    assert "health problem or medical condition" in plain
    assert "before your insurance started" in plain

    example = publication["examples"][0]
    assert "ear condition" in example["scenario"]
    assert "18 months" in example["scenario"]

    customer_text = " ".join(
        [
            publication["definition"],
            publication["plain_language_explanation"],
            publication["practical_implication"],
            example["scenario"],
            example["result"],
            example["boundary"],
            *publication["limitations"],
        ]
    ).lower()

    assert "fully covered" not in customer_text
    assert "insurer will pay" not in customer_text
    assert "claim will be paid" not in customer_text
    assert "claim will be approved" not in customer_text


def test_ped_education_does_not_publish_star_product_mechanics() -> None:
    publication = _json(PUBLICATION_PATH)

    assert publication["concept_id"] == "pre_existing_disease"
    assert publication["allowed_uses"] == ["CUSTOMER_EDUCATION"]

    product_boundary = publication["product_specific_boundary"].lower()
    assert "waiting-period duration" in product_boundary
    assert "governed product knowledge" in product_boundary

    education_text = " ".join(
        [
            publication["plain_language_explanation"],
            publication["practical_implication"],
            publication["examples"][0]["result"],
        ]
    ).lower()
    assert "buy-back" not in education_text
    assert "12 months" not in education_text
