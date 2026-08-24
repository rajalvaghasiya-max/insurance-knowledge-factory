from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory_core.canonical.copayment_multispan_binding import (
    CopaymentMultispanBinding,
    CopaymentMultispanBindingError,
)
from insurance_intelligence.benefits.copayment_rate_matrix import (
    CopaymentCalculationBasis,
    CopaymentRateMatrixCell,
    CopaymentRateMatrixError,
    CopaymentRateMatrixMechanic,
)
from insurance_intelligence.rule_certification.copayment_multispan import (
    build_copayment_multispan_certification_case,
    run_copayment_multispan_certification_case,
)


PAGE_6_HASH = "8618196b8e6301231ea75f8f9166afa91ae2e158ec3fd5aa24b12c010adce973"
PAGE_62_HASH = "42f0ddcced22cc7ce18f757c01e8de8a679d8b0772ded9ce1854094eba94b4dc"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _cells() -> list[dict[str, object]]:
    return [
        {"plan_variant": "Classic", "claimed_category": "General Ward", "percentage": 0},
        {"plan_variant": "Classic", "claimed_category": "Twin Sharing Room", "percentage": 20},
        {"plan_variant": "Classic", "claimed_category": "All Room Categories", "percentage": 50},
        {"plan_variant": "Select", "claimed_category": "General Ward", "percentage": 0},
        {"plan_variant": "Select", "claimed_category": "All Room Categories", "percentage": 40},
        {"plan_variant": "Elite", "claimed_category": "General Ward", "percentage": 0},
        {"plan_variant": "Elite", "claimed_category": "All Room Categories", "percentage": 20},
    ]


def _fixture_repo(root: Path) -> Path:
    registration_rel = (
        "knowledge/factory/registry_backed/test/v1/generic_source_registration/"
        "policy_wording_registration.json"
    )
    bundle_rel = (
        "knowledge/factory/registry_backed/test/v1/generic_source_registration/"
        "source_registration_bundle.json"
    )
    _write_json(
        root / registration_rel,
        {
            "registration_status": "source_registered_evidence_review_required",
            "document": {
                "document_id": "test_policy_wording_v1",
                "document_version_id": "test_policy_wording_v1_sha",
                "document_type": "policy_wording",
                "storage_locator": "archive/raw_pdf/test.pdf",
                "content_sha256": "a" * 64,
            },
            "evidence_review": {
                "candidates": [
                    {
                        "candidate_id": "candidate_page_6",
                        "source_page": 6,
                        "source_char_range": {"start": 100, "end": 250},
                        "text_sha256": PAGE_6_HASH,
                        "excerpt": (
                            "If you choose a room outside your plan's category, the Copayment "
                            "(as per Annexure V) will apply on the entire claim."
                        ),
                    },
                    {
                        "candidate_id": "candidate_page_62",
                        "source_page": 62,
                        "source_char_range": {"start": 500, "end": 900},
                        "text_sha256": PAGE_62_HASH,
                        "excerpt": (
                            "Annexure V - Co-payments for Room Category: Classic General Ward 0%; "
                            "Classic Twin Sharing Room 20%; Classic All Room Categories 50%; "
                            "Select General Ward 0%; Select All Room Categories 40%; "
                            "Elite General Ward 0%; Elite All Room Categories 20%."
                        ),
                    },
                ]
            },
        },
    )
    _write_json(
        root / bundle_rel,
        {
            "registration_type": "generic_source_registration_bundle_v1",
            "product_context": {
                "insurer_id": "test_insurer",
                "product_id": "test_product",
                "product_display_name": "Test Product",
                "source_scope": "reusable_generic",
            },
            "sources": [
                {
                    "document_id": "test_policy_wording_v1",
                    "document_version_id": "test_policy_wording_v1_sha",
                    "authority_role": "primary_legal",
                    "registration_output_path": registration_rel,
                }
            ],
        },
    )
    spec_rel = "docs/architecture/test_copayment_multispan_binding_spec.json"
    _write_json(
        root / spec_rel,
        {
            "schema_version": "1.0",
            "binding_type": "copayment_multispan_binding_v1",
            "binding_id": "test_room_category_copayment_matrix_v1",
            "reviewed_by_human": True,
            "generic_source_bundle_path": bundle_rel,
            "assertion": {
                "assertion_id": "test_room_category_copayment_rule_v1",
                "assertion_type": "conditional_copayment_rule",
                "semantic_key": "room_category_copayment_rate_matrix",
                "reviewed_statement": (
                    "If a room outside the plan category is chosen, Annexure V determines the "
                    "co-payment percentage and that co-payment applies on the entire claim."
                ),
                "evidence_selections": [
                    {
                        "role": "mechanism",
                        "document_id": "test_policy_wording_v1",
                        "candidate_id": "candidate_page_6",
                        "candidate_text_sha256": PAGE_6_HASH,
                    },
                    {
                        "role": "mechanism",
                        "document_id": "test_policy_wording_v1",
                        "candidate_id": "candidate_page_62",
                        "candidate_text_sha256": PAGE_62_HASH,
                    },
                ],
            },
            "mechanic": {
                "trigger_condition": (
                    "If a room outside the plan's category is chosen, the Annexure V co-payment applies."
                ),
                "applicability_scope": (
                    "Room-category co-payment under the hospitalization benefit when the chosen room "
                    "is outside the plan's category."
                ),
                "calculation_basis": "ENTIRE_CLAIM",
                "cells": _cells(),
                "instance_resolution_dependency": (
                    "Resolve the purchased plan variant and actual claimed room category from "
                    "authoritative policy-instance / claim evidence before selecting one matrix cell."
                ),
            },
            "component_evidence_candidate_ids": {
                "obligation_value": ["candidate_page_62"],
                "trigger_condition": ["candidate_page_6"],
                "applicability_scope": ["candidate_page_6"],
                "calculation_basis": ["candidate_page_6"],
            },
        },
    )
    return root / spec_rel


def test_rate_matrix_contract_preserves_zero_cells_and_instance_guard() -> None:
    mechanic = CopaymentRateMatrixMechanic(
        cells=(
            CopaymentRateMatrixCell("Classic", "General Ward", 0),
            CopaymentRateMatrixCell("Classic", "Twin Sharing Room", 20),
        ),
        trigger_condition="Room outside the plan category is chosen.",
        applicability_scope="Room-category co-payment.",
        calculation_basis=CopaymentCalculationBasis.ENTIRE_CLAIM,
        evidence_reference_ids=("doc:page6:hash", "doc:page62:hash"),
        instance_resolution_dependency="Resolve variant and claimed room from instance evidence.",
    )

    assert mechanic.cells[0].percentage == 0
    assert mechanic.instance_resolution_required is True
    assert mechanic.unlisted_combination_outcome == "UNRESOLVED"
    assert mechanic.matrix_dimensions == ("PLAN_VARIANT", "CLAIMED_ROOM_CATEGORY")


def test_rate_matrix_contract_rejects_duplicate_selector_cells() -> None:
    with pytest.raises(CopaymentRateMatrixError, match="unique"):
        CopaymentRateMatrixMechanic(
            cells=(
                CopaymentRateMatrixCell("Classic", "General Ward", 0),
                CopaymentRateMatrixCell("Classic", "General Ward", 20),
            ),
            trigger_condition="Room outside category.",
            applicability_scope="Room-category co-payment.",
            calculation_basis=CopaymentCalculationBasis.ENTIRE_CLAIM,
            evidence_reference_ids=("doc:page6:hash", "doc:page62:hash"),
            instance_resolution_dependency="Resolve instance selectors.",
        )


def test_binding_preserves_both_candidate_lineages_and_entire_claim_basis(tmp_path: Path) -> None:
    spec_path = _fixture_repo(tmp_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    manifest = CopaymentMultispanBinding().bind(
        spec=spec,
        repository_root=tmp_path,
        bound_at="2026-08-24T00:00:00+00:00",
    ).manifest

    assertion = manifest["assertions"][0]
    assert manifest["binding_type"] == "copayment_multispan_binding_v1"
    assert manifest["mechanism_evidence_span_count"] == 2
    assert [entry["candidate_id"] for entry in assertion["evidence"]] == [
        "candidate_page_6",
        "candidate_page_62",
    ]
    assert assertion["evidence"][0]["candidate_text_sha256"] == PAGE_6_HASH
    assert assertion["evidence"][1]["candidate_text_sha256"] == PAGE_62_HASH
    assert manifest["mechanic"]["calculation_basis"] == "ENTIRE_CLAIM"
    assert manifest["mechanic"]["instance_resolution_required"] is True
    assert manifest["mechanic"]["unlisted_combination_outcome"] == "UNRESOLVED"
    assert assertion["publication_status"] == "bound_not_published"


def test_binding_fails_closed_on_second_span_hash_mismatch(tmp_path: Path) -> None:
    spec_path = _fixture_repo(tmp_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["assertion"]["evidence_selections"][1]["candidate_text_sha256"] = "b" * 64

    with pytest.raises(CopaymentMultispanBindingError, match="candidate lineage mismatch"):
        CopaymentMultispanBinding().bind(spec=spec, repository_root=tmp_path)


def test_binding_requires_exact_component_evidence_map(tmp_path: Path) -> None:
    spec_path = _fixture_repo(tmp_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    del spec["component_evidence_candidate_ids"]["calculation_basis"]

    with pytest.raises(CopaymentMultispanBindingError, match="exactly cover"):
        CopaymentMultispanBinding().bind(spec=spec, repository_root=tmp_path)


def test_certification_preserves_component_level_page_attribution(tmp_path: Path) -> None:
    spec_path = _fixture_repo(tmp_path)
    case = build_copayment_multispan_certification_case(
        binding_spec_path=spec_path.relative_to(tmp_path),
        repository_root=tmp_path,
    )

    by_topic = {}
    for package in case.evidence_output.evidence_packages:
        by_topic.setdefault(package.field_or_topic, []).append(package)

    assert {package.page for package in by_topic["OBLIGATION_VALUE"]} == {62}
    assert {package.page for package in by_topic["TRIGGER_CONDITION"]} == {6}
    assert {package.page for package in by_topic["APPLICABILITY_SCOPE"]} == {6}
    assert {package.page for package in by_topic["CALCULATION_BASIS"]} == {6}
    assert by_topic["CALCULATION_BASIS"][0].evidence_role == "CALCULATION_INPUT"
    assert "Classic | General Ward = 0%" in by_topic["OBLIGATION_VALUE"][0].claim
    assert "ENTIRE_CLAIM" in by_topic["CALCULATION_BASIS"][0].claim

    result = run_copayment_multispan_certification_case(case)
    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True


def test_real_reassure_spec_encodes_exact_two_span_room_matrix_without_black_inference() -> None:
    spec = json.loads(
        Path(
            "docs/architecture/niva_bupa_reassure_3_0_room_category_copayment_multispan_binding_spec.json"
        ).read_text(encoding="utf-8")
    )

    selections = spec["assertion"]["evidence_selections"]
    assert [(item["candidate_id"], item["candidate_text_sha256"]) for item in selections] == [
        ("candidate_page_6", PAGE_6_HASH),
        ("candidate_page_62", PAGE_62_HASH),
    ]
    assert spec["mechanic"]["calculation_basis"] == "ENTIRE_CLAIM"
    assert len(spec["mechanic"]["cells"]) == 12
    assert {row["percentage"] for row in spec["mechanic"]["cells"]} == {0, 20, 40, 50}
    assert {row["plan_variant"] for row in spec["mechanic"]["cells"]} == {
        "Classic",
        "Select",
        "Elite",
    }
    assert "Black" not in {row["plan_variant"] for row in spec["mechanic"]["cells"]}
    assert spec["component_evidence_candidate_ids"]["obligation_value"] == ["candidate_page_62"]
    assert spec["component_evidence_candidate_ids"]["calculation_basis"] == ["candidate_page_6"]
    assert spec["governance"]["customer_specific_rate_authorized"] is False
    assert spec["governance"]["unlisted_matrix_combination_inference_authorized"] is False
