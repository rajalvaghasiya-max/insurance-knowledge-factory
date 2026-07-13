from __future__ import annotations

from copy import deepcopy

import pytest

from knowledge_domains.health.concept_knowledge.governed_generic_concept_record import (
    GenericConceptValidationError,
    GovernedGenericConceptRecordContract,
)
from scripts.run_copay_governed_generic_concept_record import (
    build_record,
    find_copay_mechanism,
)


def parsed_policy() -> dict:
    return {
        "pages": [
            {"page_number": 1, "text": "Unrelated content."},
            {
                "page_number": 33,
                "text": (
                    "x. Voluntary co-payment Discount "
                    "a. If the Voluntary co-payment option is opted, then a discount "
                    "corresponding to the co-payment opted would be applicable. "
                    "b. If a claim has been admitted under In-patient Hospitalization "
                    "Treatment then, the Insured shall bear a 5% or 10% or 15% or 20% "
                    "of the eligible claim amount payable under this Policy and Our "
                    "liability, if any, shall only be in excess of that sum. "
                    "29. Deductions in case of cancellation/return of Policy."
                ),
            },
        ]
    }


def record() -> dict:
    locator, page, evidence = find_copay_mechanism(parsed_policy())
    return build_record(
        source_pdf_relative="archive/raw_pdf/example/policy.pdf",
        parsed_path_relative="processed/pdf_parse/example.json",
        source_sha256="a" * 64,
        evidence_locator=locator,
        evidence_page=page,
        evidence_text=evidence,
        reviewer_identity="reviewer",
        reviewed_at="2026-07-12T10:00:00Z",
        created_by="reviewer",
        created_at="2026-07-12T10:01:00Z",
    )


def test_finds_bounded_copay_mechanism() -> None:
    locator, page, evidence = find_copay_mechanism(parsed_policy())
    assert locator == "$.pages[1].text"
    assert page == 33
    assert evidence.startswith("Voluntary co-payment Discount")
    assert "Insured shall bear" in evidence
    assert "29. Deductions" not in evidence


def test_builds_governed_copay_record() -> None:
    result = record()
    assert result["concept_id"] == "copay"
    assert result["record_type"] == "governed_generic_concept_record_v0_2"
    assert result["source_evidence"][0]["source_type"] == (
        "insurer_policy_wording_generic_mechanism"
    )
    assert result["publication_state"] == "not_published"
    assert result["customer_answer_state"] == "not_created"


def test_record_is_deterministic() -> None:
    assert record()["record_id"] == record()["record_id"]


def test_rejects_missing_product_context_exclusion() -> None:
    result = record()
    unsafe = deepcopy(result)
    unsafe.pop("record_id")
    unsafe["source_evidence"][0]["product_context_excluded"] = False
    with pytest.raises(GenericConceptValidationError, match="product_context_excluded"):
        GovernedGenericConceptRecordContract.validate_record(unsafe)


def test_generic_definition_avoids_unsafe_absolutes() -> None:
    payload = str(record()).lower()
    assert "applies to every claim" not in payload
    assert "insurer always pays" not in payload
    assert "total hospital bill" in payload
    assert "does not automatically pay the entire remaining percentage" in payload
