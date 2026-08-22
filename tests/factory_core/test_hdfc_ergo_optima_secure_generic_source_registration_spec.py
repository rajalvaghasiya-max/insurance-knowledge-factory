from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = (
    ROOT
    / "docs"
    / "architecture"
    / "hdfc_ergo_optima_secure_current_version_generic_sources_registration_spec.json"
)


def _spec() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


def test_hdfc_registration_spec_uses_existing_generic_contract() -> None:
    spec = _spec()
    assert spec["schema_version"] == "1.0"
    assert spec["registration_type"] == "generic_source_registration_bundle_v1"
    assert spec["product_context"] == {
        "insurer_id": "hdfc_ergo",
        "product_id": "optima_secure",
        "product_display_name": "my: Optima Secure",
        "source_scope": "reusable_generic",
        "reviewed_generic_source_confirmation": True,
    }


def test_hdfc_registration_spec_is_bound_to_exact_acquired_artifact() -> None:
    document = _spec()["documents"][0]
    sha = "694c0540cb341ec9254c08a41668174b60d4a7ebc4833d78505052367c0b6ab3"

    assert document["document_id"] == "hdfc_ergo_optima_secure_policy_wording_v8"
    assert document["source_document_id"] == sha
    assert document["authority_role"] == "primary_legal"
    assert document["document_type"] == "policy_wording"
    assert sha in document["document_path"]
    assert sha in document["extracted_text_output_path"]
    assert document["registration_output_path"] == (
        "knowledge/factory/registry_backed/hdfc_ergo_optima_secure/v8/"
        "generic_source_registration/policy_wording_registration.json"
    )


def test_hdfc_registration_markers_anchor_current_product_and_semantic_pressure() -> None:
    document = _spec()["documents"][0]
    markers = set(document["evidence_markers"])

    assert "Optima Secure" in markers
    assert "HDFHLIP26058V082526" in markers
    assert "Waiting Period" in markers
    assert "Co-payment" in markers
    assert document["source_issued_label"] == (
        "for policies with period of Insurance starting 02-April-2026 onwards"
    )


def test_registration_spec_adds_no_runtime_python_surface() -> None:
    assert SPEC.suffix == ".json"
    checkpoint = json.loads(
        (
            ROOT
            / "docs"
            / "architecture"
            / "hdfc_ergo_optima_secure_cold_start_acquisition_2026-08-22.json"
        ).read_text(encoding="utf-8")
    )
    assert checkpoint["cold_start_governance"]["new_runtime_python_budget"] == 0
