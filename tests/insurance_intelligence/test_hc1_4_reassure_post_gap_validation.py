from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path

from factory_core.canonical.generic_legal_condition_binding import GenericLegalConditionBinding
from insurance_intelligence.benefits.copayment_composition import (
    CopaymentCompositionType,
    resolve_copayment_composition,
)
from insurance_intelligence.rule_certification.conditional_copayment import (
    build_conditional_copayment_certification_cases,
    run_conditional_copayment_certification_cases,
)


PRODUCT5_RESULT = Path("docs/architecture/health_product5_repeatability_result_2026-08-24.json")
WAITING_GAP = Path(
    "docs/architecture/niva_bupa_reassure_3_0_waiting_period_representation_gap_2026-08-24.json"
)
COPAY_GAP = Path(
    "docs/architecture/niva_bupa_reassure_3_0_copayment_representation_gap_2026-08-24.json"
)
POST_GAP = Path("docs/architecture/niva_bupa_reassure_3_0_post_gap_validation_2026-08-24.json")
PERSONAL_WAIT_SPEC = Path(
    "docs/architecture/niva_bupa_reassure_3_0_personal_underwriting_waiting_period_binding_spec.json"
)
ADDITIVE_SPEC = Path(
    "docs/architecture/niva_bupa_reassure_3_0_additive_cumulative_copayment_binding_spec.json"
)
ROOM_MATRIX_SPEC = Path(
    "docs/architecture/niva_bupa_reassure_3_0_room_category_copayment_multispan_binding_spec.json"
)

PAGE_33_HASH = "74408d4896f75d5127ed7ef4109bd7229a184c9c2589a6ac5dfe30f653579015"
PAGE_44_HASH = "37c05717baaf50fd15af0789332fc8dad9eadda19018b86755330041f0acc52d"
PAGE_45_HASH = "ffea1ca232b2297bafeca6c9856968b1136b7e8cf217a25aa01dc202e48a2f46"
PAGE_6_HASH = "8618196b8e6301231ea75f8f9166afa91ae2e158ec3fd5aa24b12c010adce973"
PAGE_62_HASH = "42f0ddcced22cc7ce18f757c01e8de8a679d8b0772ded9ce1854094eba94b4dc"


EXPECTED_HISTORICAL_BLOBS = {
    PRODUCT5_RESULT: "e3fe3159bf56d0a4c13d5fbdfa634d07de823910",
    WAITING_GAP: "a75899b561989b35bebb39a2a26077dfcf4a78b9",
    COPAY_GAP: "ab15d1a3b8e40c4d46191b5710f7d6f832b18aff",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    header = f"blob {len(raw)}\0".encode("ascii")
    return sha1(header + raw).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _fixture_additive_repo(root: Path) -> tuple[Path, Path]:
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
                "document_id": "niva_bupa_reassure_3_0_policy_wording_v1",
                "document_version_id": "niva_bupa_reassure_3_0_policy_wording_v1_sha",
                "document_type": "policy_wording",
                "storage_locator": "archive/raw_pdf/niva_bupa/reassure_3_0.pdf",
                "content_sha256": "a" * 64,
            },
            "evidence_review": {
                "candidates": [
                    {
                        "candidate_id": "candidate_page_44",
                        "source_page": 44,
                        "source_char_range": {"start": 100, "end": 300},
                        "text_sha256": PAGE_44_HASH,
                        "excerpt": (
                            "Failure to intimate prolonged hospitalization triggers an additional "
                            "cumulative co-payment of 10%."
                        ),
                    },
                    {
                        "candidate_id": "candidate_page_45",
                        "source_page": 45,
                        "source_char_range": {"start": 400, "end": 650},
                        "text_sha256": PAGE_45_HASH,
                        "excerpt": (
                            "Specified non-network organ-transplant process failures trigger an "
                            "additional co-payment of 20%."
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
                "insurer_id": "niva_bupa",
                "product_id": "reassure_3_0",
                "product_display_name": "Niva Bupa ReAssure 3.0",
                "source_scope": "reusable_generic",
            },
            "sources": [
                {
                    "document_id": "niva_bupa_reassure_3_0_policy_wording_v1",
                    "document_version_id": "niva_bupa_reassure_3_0_policy_wording_v1_sha",
                    "authority_role": "primary_legal",
                    "registration_output_path": registration_rel,
                }
            ],
        },
    )
    spec = _load(ADDITIVE_SPEC)
    spec["generic_source_bundle_path"] = bundle_rel
    spec_rel = "docs/architecture/reassure_additive_fixture_spec.json"
    _write_json(root / spec_rel, spec)

    manifest = GenericLegalConditionBinding().bind(
        spec=spec,
        repository_root=root,
        bound_at="2026-08-24T00:00:00+00:00",
    ).manifest
    manifest_rel = "knowledge/factory/registry_backed/test/reassure_additive_binding.json"
    _write_json(root / manifest_rel, manifest)
    return root / spec_rel, root / manifest_rel


def test_historical_product5_and_gap_records_remain_bitwise_unchanged() -> None:
    for path, expected_blob in EXPECTED_HISTORICAL_BLOBS.items():
        assert _git_blob_sha(path) == expected_blob

    initial = _load(PRODUCT5_RESULT)
    assert initial["target_concepts"]["waiting_period"]["classification"] == "REPRESENTATION_GAP"
    assert initial["target_concepts"]["copayment"]["classification"] == "REPRESENTATION_GAP"
    assert initial["protocol_outcome"]["classification"] == "REPEATABILITY_NOT_PROVEN"
    assert initial["protocol_outcome"]["repeatability_proven"] is False


def test_personal_underwriting_gap_is_now_represented_without_scalar_coercion() -> None:
    spec = _load(PERSONAL_WAIT_SPEC)

    assert spec["binding_type"] == "personal_underwriting_waiting_period_binding_v1"
    assert spec["evidence_selection"]["candidate_id"] == "candidate_page_33"
    assert spec["evidence_selection"]["candidate_text_sha256"] == PAGE_33_HASH
    assert spec["mechanic"]["maximum_duration_value"] == 48
    assert spec["mechanic"]["maximum_duration_unit"] == "MONTHS"
    assert "individual insured person" in spec["mechanic"]["applies_to"][0]
    assert spec["governance"]["maximum_bound_must_not_be_rendered_as_exact_customer_duration"] is True
    assert spec["governance"]["customer_specific_conditions_resolved"] is False
    assert spec["governance"]["customer_specific_duration_resolved"] is False


def test_reassure_additive_cumulative_assertions_bind_and_certify_after_hc1_2(tmp_path: Path) -> None:
    _, manifest_path = _fixture_additive_repo(tmp_path)
    bundle = build_conditional_copayment_certification_cases(
        binding_manifest_path=manifest_path.relative_to(tmp_path),
        repository_root=tmp_path,
    )
    results = run_conditional_copayment_certification_cases(bundle)

    assert len(results) == 2
    assert all(result.outcome == "PASS" for result in results)
    assert all(result.actual_completeness_status == "COMPLETE" for result in results)
    assert all(result.actual_explanation_permitted is True for result in results)

    spec = _load(ADDITIVE_SPEC)
    statements = {item["evidence_selections"][0]["candidate_id"]: item["reviewed_statement"] for item in spec["assertions"]}
    page44 = resolve_copayment_composition(statements["candidate_page_44"])
    page45 = resolve_copayment_composition(statements["candidate_page_45"])

    assert page44.composition_type is CopaymentCompositionType.CUMULATIVE
    assert page44.stacks_with_other_cost_sharing is True
    assert page45.composition_type is CopaymentCompositionType.ADDITIVE
    assert page45.stacks_with_other_cost_sharing is True


def test_reassure_additive_spec_is_hash_locked_and_does_not_authorize_customer_liability() -> None:
    spec = _load(ADDITIVE_SPEC)
    selections = [item["evidence_selections"][0] for item in spec["assertions"]]

    assert [(item["candidate_id"], item["candidate_text_sha256"]) for item in selections] == [
        ("candidate_page_44", PAGE_44_HASH),
        ("candidate_page_45", PAGE_45_HASH),
    ]
    assert spec["governance"]["publication_authorized"] is False
    assert spec["governance"]["customer_specific_trigger_resolution_authorized"] is False
    assert spec["governance"]["combined_customer_liability_calculation_authorized"] is False
    assert spec["governance"]["claim_payment_inference_authorized"] is False


def test_room_matrix_gap_is_now_multispan_and_component_attributed() -> None:
    spec = _load(ROOM_MATRIX_SPEC)
    selections = spec["assertion"]["evidence_selections"]

    assert [(item["candidate_id"], item["candidate_text_sha256"]) for item in selections] == [
        ("candidate_page_6", PAGE_6_HASH),
        ("candidate_page_62", PAGE_62_HASH),
    ]
    assert spec["component_evidence_candidate_ids"] == {
        "obligation_value": ["candidate_page_62"],
        "trigger_condition": ["candidate_page_6"],
        "applicability_scope": ["candidate_page_6"],
        "calculation_basis": ["candidate_page_6"],
    }
    assert spec["mechanic"]["calculation_basis"] == "ENTIRE_CLAIM"
    assert len(spec["mechanic"]["cells"]) == 12
    assert {cell["percentage"] for cell in spec["mechanic"]["cells"]} == {0, 20, 40, 50}
    assert {cell["plan_variant"] for cell in spec["mechanic"]["cells"]} == {
        "Classic",
        "Select",
        "Elite",
    }
    assert spec["governance"]["customer_specific_rate_authorized"] is False
    assert spec["governance"]["unlisted_matrix_combination_inference_authorized"] is False


def test_post_gap_checkpoint_closes_only_observed_gaps_not_repeatability() -> None:
    checkpoint = _load(POST_GAP)

    assert checkpoint["validation_status"] == "OBSERVED_REPRESENTATION_GAPS_VALIDATED_CLOSED"
    assert checkpoint["validated_from_main_commit"] == "0e1d4816f418c8000224fd627a17a2ef3e1731d9"
    assert [item["milestone"] for item in checkpoint["earned_extensions"]] == [
        "HC-1.1",
        "HC-1.2",
        "HC-1.3",
    ]
    assert all(
        item["post_gap_validation"] == "VALIDATED_FOR_OBSERVED_SHAPE"
        for item in checkpoint["earned_extensions"]
    )
    outcome = checkpoint["post_gap_outcome"]
    assert outcome["reassure_observed_representation_gaps_remaining"] == 0
    assert outcome["observed_gap_shapes_representable"] is True
    assert outcome["observed_gap_shapes_bindable_or_certifiable"] is True
    assert outcome["historical_repeatability_outcome_changed"] is False
    assert outcome["repeatability_proven_by_this_checkpoint"] is False
    assert outcome["neutral_cold_start_still_required_for_repeatability_proof"] is True
    assert checkpoint["governance"]["unknown_variant_space_open"] is True
    assert checkpoint["governance"]["known_gap_set_claimed_exhaustive"] is False
