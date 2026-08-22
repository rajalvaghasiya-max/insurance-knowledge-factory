from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT = (
    ROOT
    / "docs"
    / "architecture"
    / "hdfc_ergo_optima_secure_cold_start_acquisition_2026-08-22.json"
)


def _checkpoint() -> dict:
    return json.loads(CHECKPOINT.read_text(encoding="utf-8"))


def test_cold_start_uses_current_hdfc_optima_secure_identity() -> None:
    checkpoint = _checkpoint()
    product = checkpoint["product"]
    source = checkpoint["official_source"]

    assert product["insurer_id"] == "hdfc_ergo"
    assert product["product_id"] == "optima_secure"
    assert product["uin"] == "HDFHLIP26058V082526"
    assert product["cold_start_status"] == "TRUE_COLD_START"
    assert source["observed_uin"] == product["uin"]
    assert source["authority_role"] == "primary_legal"
    assert source["observed_page_count"] == 69


def test_acquisition_is_bound_to_immutable_local_artifact_identity() -> None:
    checkpoint = _checkpoint()
    source = checkpoint["official_source"]
    governance = checkpoint["cold_start_governance"]

    assert source["acquisition_status"] == "ACQUIRED_AND_TEXT_VALIDATED"
    assert source["source_document_id_sha256"] == (
        "694c0540cb341ec9254c08a41668174b60d4a7ebc4833d78505052367c0b6ab3"
    )
    assert source["observed_pdf_bytes"] == 928993
    assert source["observed_text_bytes"] == 175340
    assert source["local_document_path"].endswith(".pdf")
    assert source["local_extracted_text_path"].endswith(".txt")
    assert all(source["text_validation"].values())
    assert governance["registration_authorized"] is True
    assert governance["reason_registration_blocked"] is None
    assert governance["source_document_id_must_not_be_guessed"] is True


def test_cold_start_still_has_zero_new_runtime_python_budget() -> None:
    checkpoint = _checkpoint()
    governance = checkpoint["cold_start_governance"]
    reuse = set(checkpoint["observed_architecture_pressure"]["expected_generic_reuse"])

    assert governance["new_runtime_python_budget"] == 0
    assert governance["registration_passed_without_runtime_python_changes"] is True
    assert "WaitingPeriodMechanic" in reuse
    assert "WaitingPeriodBinding" in reuse
    assert "generic source registration" in reuse


def test_no_downstream_promotion_is_authorized_by_registration() -> None:
    governance = _checkpoint()["cold_start_governance"]

    assert governance["publication_authorized"] is False
    assert governance["coverage_registry_promotion_authorized"] is False
    assert governance["comparison_ready_authorized"] is False
    assert governance["decision_support_ready_authorized"] is False
    assert governance["human_evidence_review_required_before_binding"] is True


def test_next_gate_is_candidate_review_and_generic_binding_attempt() -> None:
    gate = _checkpoint()["next_gate"]

    assert gate["gate_id"] == "REVIEW_CANDIDATES_AND_ATTEMPT_GENERIC_SEMANTIC_BINDING"
    assert "reviewed copayment evidence candidates" in gate["required_outputs"]
    assert "reviewed waiting-period evidence candidates" in gate["required_outputs"]
    assert "first HDFC binding attempt using existing generic contracts" in gate["required_outputs"]
    assert "representational gap" in gate["success_condition"]
