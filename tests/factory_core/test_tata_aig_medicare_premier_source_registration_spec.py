import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs/architecture/tata_aig_medicare_premier_current_version_generic_sources_registration_spec.json"
CHECKPOINT = ROOT / "docs/architecture/tata_aig_medicare_premier_cold_start_acquisition_2026-08-23.json"
EXPECTED_HASH = "392feaeeb26cb9ec7f6addc3ed764291d9c9f16bf6c70f466d9f92f85db78960"
EXPECTED_UIN = "TATHLIP26052V052526"


def test_tata_medicare_premier_registration_spec_is_hash_locked_primary_legal() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert spec["registration_type"] == "generic_source_registration_bundle_v1"
    assert spec["product_context"]["insurer_id"] == "tata_aig_general"
    assert spec["product_context"]["product_id"] == "medicare_premier"
    assert spec["product_context"]["source_scope"] == "reusable_generic"
    assert len(spec["documents"]) == 1
    document = spec["documents"][0]
    assert document["document_type"] == "policy_wording"
    assert document["authority_role"] == "primary_legal"
    assert document["source_document_id"] == EXPECTED_HASH
    assert EXPECTED_UIN in document["evidence_markers"]
    assert EXPECTED_HASH in document["document_path"]
    assert EXPECTED_HASH in document["extracted_text_output_path"]


def test_tata_cold_start_checkpoint_preserves_repeatability_freeze() -> None:
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    assert checkpoint["baseline_commit_sha"] == "bda5eb8721e04f8a78118ca4c4e054a09520a6d4"
    assert checkpoint["product"]["uin"] == EXPECTED_UIN
    assert checkpoint["official_source"]["source_document_id_sha256"] == EXPECTED_HASH
    assert checkpoint["official_source"]["observed_pdf_bytes"] == 554394
    integrity = checkpoint["experiment_integrity"]
    assert integrity["target_concept_evidence_review_started_before_selection"] is False
    assert integrity["generic_runtime_changed"] is False
    assert integrity["decision_logic_added_in_config"] is False
    assert integrity["registration_uses_existing_generic_runtime"] is True
    assert integrity["semantic_binding_authorized_before_registration"] is False
