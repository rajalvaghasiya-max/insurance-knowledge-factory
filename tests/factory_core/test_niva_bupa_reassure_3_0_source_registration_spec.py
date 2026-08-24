from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_reassure3_source_registration_is_hash_locked_and_declarative() -> None:
    path = ROOT / "docs/architecture/niva_bupa_reassure_3_0_current_version_generic_sources_registration_spec.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["registration_type"] == "generic_source_registration_bundle_v1"
    assert data["product_context"]["insurer_id"] == "niva_bupa"
    assert data["product_context"]["product_id"] == "reassure_3_0"

    assert len(data["documents"]) == 1
    document = data["documents"][0]
    assert document["document_id"] == "niva_bupa_reassure_3_0_policy_wording_v1"
    assert document["authority_role"] == "primary_legal"
    assert document["source_document_id"] == "04c06f045979be509e124e1d802fed47097f0995132ff94cfd67aafbaf2fa12f"
    assert document["document_path"].endswith(
        "Niva-Bupa-ReAssure-3.0__04c06f045979be509e124e1d802fed47097f0995132ff94cfd67aafbaf2fa12f.pdf"
    )

    serialized = json.dumps(data).lower()
    assert '"percentage"' not in serialized
    assert '"duration_value"' not in serialized
    assert '"does_not_apply"' not in serialized
    assert '"0%"' not in serialized


def test_reassure3_acquisition_rejects_the_failed_first_download_and_locks_valid_pdf() -> None:
    path = ROOT / "docs/architecture/niva_bupa_reassure_3_0_cold_start_acquisition_2026-08-24.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    source = data["source"]
    assert source["content_sha256"] == "04c06f045979be509e124e1d802fed47097f0995132ff94cfd67aafbaf2fa12f"
    assert source["byte_size"] == 295089
    assert source["file_signature_verified"] == "%PDF-1.7"
    assert data["governance"]["target_concept_semantic_review_started"] is False
    assert data["governance"]["frozen_runtime_changes"] == 0
    assert any("1040-byte non-PDF" in note for note in data["acquisition_notes"])
