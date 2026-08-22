from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RECORD = (
    ROOT
    / "docs"
    / "architecture"
    / "hdfc_ergo_optima_secure_generic_registration_execution_2026-08-22.json"
)
CHECKPOINT = (
    ROOT
    / "docs"
    / "architecture"
    / "hdfc_ergo_optima_secure_cold_start_acquisition_2026-08-22.json"
)


def _record() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8"))


def _checkpoint() -> dict:
    return json.loads(CHECKPOINT.read_text(encoding="utf-8"))


def test_hdfc_generic_registration_execution_passed_with_primary_legal_source() -> None:
    record = _record()
    source = record["sources"][0]

    assert record["registration_status"] == "generic_sources_registered_evidence_review_required"
    assert record["source_count"] == 1
    assert source["authority_role"] == "primary_legal"
    assert source["evidence_candidate_count"] == 69
    assert source["registration_status"] == "source_registered_evidence_review_required"


def test_hdfc_cold_start_registration_used_zero_new_runtime_python() -> None:
    measurement = _record()["cold_start_measurement"]
    checkpoint = _checkpoint()["cold_start_governance"]

    assert measurement["new_runtime_python_files"] == 0
    assert measurement["runtime_python_changes"] == 0
    assert measurement["insurer_specific_runtime_code_required"] is False
    assert measurement["generic_source_registration_reused_unchanged"] is True
    assert measurement["result"] == "PASS"
    assert checkpoint["registration_passed_without_runtime_python_changes"] is True


def test_registration_does_not_promote_unreviewed_evidence() -> None:
    governance = _record()["governance"]
    checkpoint = _checkpoint()

    assert governance["evidence_candidates_require_human_review"] is True
    assert governance["binding_authorized_before_review"] is False
    assert governance["publication_authorized"] is False
    assert governance["benefit_inference_from_registration_alone"] is False
    assert governance["coverage_registry_promotion_authorized"] is False
    assert checkpoint["next_gate"]["gate_id"] == (
        "REVIEW_CANDIDATES_AND_ATTEMPT_GENERIC_SEMANTIC_BINDING"
    )
