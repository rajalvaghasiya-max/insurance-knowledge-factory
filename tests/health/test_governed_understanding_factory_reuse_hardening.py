
from copy import deepcopy
import json
from pathlib import Path

import pytest

from knowledge_domains.health.concept_knowledge.governed_concept_to_meaning_asset import (
    GovernedConceptToMeaningAssetAdapter,
)
from knowledge_domains.health.understanding_manufacturing.learning_primitive_manufacturing_line import (
    LearningPrimitiveManufacturingLine,
)


def record(concept_id: str) -> dict:
    is_copay = concept_id == "copay"
    return {
        "record_id": f"gconcept_test_{concept_id}",
        "record_type": "governed_generic_concept_record_v0_2",
        "schema_version": "0.2",
        "concept_id": concept_id,
        "concept_name": "Copay" if is_copay else "Deductible",
        "concept_scope": "generic_insurance_concept",
        "domain": "health_insurance",
        "definition": (
            "A copay is a policy cost-sharing condition under which the insured "
            "bears a stated percentage of an amount determined under applicable "
            "policy terms when the copay applies."
            if is_copay
            else "A deductible applies before eligible insurer payment."
        ),
        "plain_language_explanation": (
            "The percentage and calculation base must be checked in the policy."
            if is_copay
            else "It is borne before insurer assessment."
        ),
        "practical_implication": (
            "The insured may bear a percentage when the documented copay applies."
            if is_copay
            else "It may increase out-of-pocket exposure."
        ),
        "simple_example": (
            {
                "policy_defined_calculation_base": 90000,
                "copay_percentage": 20,
                "insured_borne_copay_amount": 18000,
                "boundary": "Illustrative only.",
            }
            if is_copay
            else {
                "eligible_expense": 300000,
                "deductible": 100000,
                "balance_for_insurer_assessment": 200000,
            }
        ),
        "common_misunderstandings": [
            (
                "Copay does not automatically apply to every claim."
                if is_copay
                else "The insurer does not automatically pay everything above it."
            )
        ],
        "limitations": ["No product-specific value is stated."],
        "product_specific_boundary": (
            "Applicability, percentage, and calculation base come from governed "
            "product knowledge."
        ),
        "customer_document_boundary": (
            "Customer selection comes from the policy schedule or other applicable "
            "customer document."
        ),
        "related_concepts": (
            ["deductible", "admissible_claim"]
            if is_copay
            else ["copay", "aggregate_deductible"]
        ),
        "source_evidence": [{
            "evidence_id": f"{concept_id}_evidence_001",
            "source_type": "insurer_policy_wording_standard_definition",
            "source_title": "Policy wording",
            "publisher": "Example insurer",
            "source_locator": "knowledge/example/parsed/policy_wording.json::$.pages[1].text",
            "source_document_path": "knowledge/example/documents/policy_wording.pdf",
            "source_sha256": "a" * 64,
            "evidence_text": f"{concept_id} evidence.",
            "hosting_document_scope": "product_specific",
            "extracted_content_scope": "generic_insurance_concept",
            "product_context_excluded": True,
        }],
        "review_decision": {
            "review_decision_id": f"review_{concept_id}",
            "decision": "approve_for_governed_generic_concept_creation",
            "reviewer_identity": "reviewer",
            "reviewed_at": "2026-07-11T10:00:00Z",
            "rationale": "Reviewed for generic use.",
        },
        "knowledge_version": "1.0",
        "publication_state": "not_published",
        "customer_answer_state": "not_created",
        "entitlement_state": "not_evaluated",
        "recommendation_state": "not_created",
        "created_by": "test",
        "created_at": "2026-07-11T10:05:00Z",
        "factory_signature": {
            "factory": "PolicyScna Knowledge Factory",
            "engine_version": "0.2",
            "rules_version": "0.2",
            "schema_version": "0.2",
            "deterministic": True,
        },
    }


def test_deductible_profile_preserves_existing_semantics() -> None:
    asset = GovernedConceptToMeaningAssetAdapter.build(record("deductible"))
    assert asset["trigger"] == (
        "The applicable deductible is evaluated before eligible insurer "
        "benefits become payable, subject to policy terms."
    )
    assert asset["inputs"] == [
        "eligible_expense",
        "applicable_deductible",
        "policy_terms",
        "claim_admissibility",
    ]
    assert asset["outputs"] == [
        "insured_borne_deductible",
        "balance_for_insurer_assessment",
    ]


def test_copay_profile_has_no_deductible_semantic_leakage() -> None:
    asset = GovernedConceptToMeaningAssetAdapter.build(record("copay"))
    payload = json.dumps(asset, ensure_ascii=False).lower()

    assert asset["concept_id"] == "copay"
    assert asset["inputs"] == [
        "applicable_copay_percentage",
        "policy_defined_calculation_base",
        "copay_applicability",
        "policy_terms",
    ]
    assert asset["outputs"] == [
        "insured_borne_copay_amount",
        "remaining_amount_for_insurer_assessment",
    ]
    assert "applicable_deductible" not in payload
    assert "insured_borne_deductible" not in payload
    assert "every approved insurance claim" not in payload
    assert "guaranteed insurer payment" in payload


def test_unknown_concept_fails_closed() -> None:
    unsupported = record("deductible")
    unsupported["concept_id"] = "unknown_cost_share"
    unsupported["concept_name"] = "Unknown Cost Share"
    with pytest.raises(Exception, match="unsupported concept profile"):
        GovernedConceptToMeaningAssetAdapter.build(unsupported)


def test_adapter_remains_deterministic_and_non_mutating() -> None:
    source = record("copay")
    original = deepcopy(source)
    first = GovernedConceptToMeaningAssetAdapter.build(source)
    second = GovernedConceptToMeaningAssetAdapter.build(source)
    assert first["asset_id"] == second["asset_id"]
    assert source == original


def test_governed_copay_uses_generic_primitive_path(tmp_path: Path) -> None:
    meaning = GovernedConceptToMeaningAssetAdapter.build(record("copay"))
    input_path = tmp_path / "copay_meaning.json"
    output_dir = tmp_path / "out"
    input_path.write_text(json.dumps(meaning), encoding="utf-8")

    result = LearningPrimitiveManufacturingLine(
        input_path=input_path,
        output_dir=output_dir,
        factory_version="1.0",
    ).run()

    asset = json.loads(Path(result["asset"]).read_text(encoding="utf-8"))
    certification = json.loads(
        Path(result["certification"]).read_text(encoding="utf-8")
    )
    primitive_types = {p["primitive_type"] for p in asset["primitives"]}
    payload = json.dumps(asset, ensure_ascii=False).lower()

    assert certification["validation_status"] == "passed"
    assert len(asset["primitives"]) >= 6
    assert "suitability" not in primitive_types
    assert "recommendation" not in payload
    assert "fixed percentage of every approved insurance claim" not in payload
    assert "insurance pays remaining approved amount" not in payload
    assert "policies with copay usually cost less" not in payload


def test_legacy_copay_branch_remains_available() -> None:
    meaning = GovernedConceptToMeaningAssetAdapter.build(record("copay"))
    meaning.pop("governance")
    line = object.__new__(LearningPrimitiveManufacturingLine)
    primitives = line._build_primitives(meaning, meaning["evidence_refs"])
    assert len(primitives) >= 10
    assert any(p.primitive_type == "suitability" for p in primitives)
