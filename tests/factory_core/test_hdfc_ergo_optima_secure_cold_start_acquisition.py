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
    assert source["policy_period_applicability_label"] == (
        "for policies with period of Insurance starting 02-April-2026 onwards"
    )


def test_acquisition_fails_closed_until_immutable_pdf_identity_exists() -> None:
    checkpoint = _checkpoint()
    source = checkpoint["official_source"]
    governance = checkpoint["cold_start_governance"]

    assert source["acquisition_status"] == "IDENTIFIED_NOT_YET_ACQUIRED"
    assert source["source_document_id_sha256"] is None
    assert source["local_document_path"] is None
    assert source["local_extracted_text_path"] is None
    assert governance["registration_authorized"] is False
    assert governance["source_document_id_must_not_be_guessed"] is True


def test_cold_start_begins_with_zero_new_runtime_python_budget() -> None:
    checkpoint = _checkpoint()
    governance = checkpoint["cold_start_governance"]
    reuse = set(checkpoint["observed_architecture_pressure"]["expected_generic_reuse"])

    assert governance["new_runtime_python_budget"] == 0
    assert "WaitingPeriodMechanic" in reuse
    assert "WaitingPeriodBinding" in reuse
    assert "generic source registration" in reuse


def test_no_downstream_promotion_is_authorized_before_registration() -> None:
    governance = _checkpoint()["cold_start_governance"]

    assert governance["publication_authorized"] is False
    assert governance["coverage_registry_promotion_authorized"] is False
    assert governance["comparison_ready_authorized"] is False
    assert governance["decision_support_ready_authorized"] is False


def test_next_gate_requires_real_artifact_and_existing_generic_registration() -> None:
    gate = _checkpoint()["next_gate"]

    assert gate["gate_id"] == "ACQUIRE_IMMUTABLE_PRIMARY_LEGAL_ARTIFACT"
    assert "SHA256 of exact PDF bytes" in gate["required_outputs"]
    assert "deterministically extracted text" in gate["required_outputs"]
    assert "generic source registration bundle with evidence candidates" in gate["required_outputs"]
    assert "without insurer-specific Python changes" in gate["success_condition"]
