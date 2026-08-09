from __future__ import annotations

import json
from pathlib import Path

import pytest

from insurance_intelligence.benefits.processed_waiting_period_evidence_audit import (
    ProcessedEvidenceAuditStatus,
    ProcessedWaitingPeriodAuditError,
    audit_all_processed_waiting_period_candidates,
    audit_processed_waiting_period_candidates,
    load_processed_document,
)
from insurance_intelligence.benefits.waiting_period_contracts import WaitingPeriodType


DOCUMENT_ID = "doc_d20a8488ecb3243f6de2"
ASSET_ID = "pdoc_72d03e57d4b49c68d69a11fc"
SOURCE_SHA256 = "e04bc4575d35e10bc86707ceeb839adf8a59f579bd27584c1b9000201bdac217"
SOURCE_PATH = Path(
    "knowledge/factory/processed_documents/"
    "doc_d20a8488ecb3243f6de2_pdoc_72d03e57d4b49c68d69a11fc_processed_document_v2.json"
)


def _audit(payload, waiting_period_type):
    return audit_processed_waiting_period_candidates(
        payload,
        waiting_period_type,
        document_id=DOCUMENT_ID,
        processed_document_asset_id=ASSET_ID,
        source_document_sha256=SOURCE_SHA256,
    )


def test_real_activ_one_processed_asset_is_available_and_loadable() -> None:
    payload = load_processed_document(SOURCE_PATH)
    assert isinstance(payload, dict)


def test_real_asset_isolates_all_three_base_waiting_period_candidate_groups() -> None:
    payload = load_processed_document(SOURCE_PATH)
    results = audit_all_processed_waiting_period_candidates(
        payload,
        document_id=DOCUMENT_ID,
        processed_document_asset_id=ASSET_ID,
        source_document_sha256=SOURCE_SHA256,
    )

    assert [item.waiting_period_type for item in results] == [
        WaitingPeriodType.INITIAL,
        WaitingPeriodType.SPECIFIC_DISEASE_PROCEDURE,
        WaitingPeriodType.PRE_EXISTING_DISEASE,
    ]
    assert all(item.status is ProcessedEvidenceAuditStatus.REVIEW_REQUIRED for item in results)
    assert all(item.candidates for item in results)


def test_real_asset_candidates_preserve_exact_uin_context_where_present() -> None:
    payload = load_processed_document(SOURCE_PATH)
    results = audit_all_processed_waiting_period_candidates(
        payload,
        document_id=DOCUMENT_ID,
        processed_document_asset_id=ASSET_ID,
        source_document_sha256=SOURCE_SHA256,
    )
    combined = "\n".join(
        candidate.excerpt for result in results for candidate in result.candidates
    )
    assert "ADIHLIP24097V012324" in combined


def test_specific_disease_audit_preserves_optional_reduction_as_review_candidate() -> None:
    payload = load_processed_document(SOURCE_PATH)
    result = _audit(payload, WaitingPeriodType.SPECIFIC_DISEASE_PROCEDURE)
    combined = "\n".join(item.excerpt for item in result.candidates)
    assert "Reduction in Speci" in combined or "Reduction in Specific Disease Waiting Period" in combined


def test_candidate_isolation_does_not_publish_or_choose_base_clause() -> None:
    payload = load_processed_document(SOURCE_PATH)
    result = _audit(payload, WaitingPeriodType.PRE_EXISTING_DISEASE)
    assert result.status is ProcessedEvidenceAuditStatus.REVIEW_REQUIRED
    assert not hasattr(result, "approved_candidate_id")
    assert not hasattr(result, "waiting_period_mechanic")


def test_duplicate_text_nodes_are_deduplicated_deterministically() -> None:
    payload = {
        "items": [
            {"page_number": 10, "text": "D.1.3 30-day Waiting Period (Code-Excl03)"},
            {"page_number": 99, "text": "D.1.3 30-day Waiting Period (Code-Excl03)"},
        ]
    }
    result = _audit(payload, WaitingPeriodType.INITIAL)
    assert len(result.candidates) == 1
    assert result.candidates[0].source_page == 10


def test_non_matching_document_fails_closed_with_no_candidate() -> None:
    result = _audit({"text": "No waiting-period clause here."}, WaitingPeriodType.INITIAL)
    assert result.status is ProcessedEvidenceAuditStatus.NO_CANDIDATE
    assert result.candidates == ()


def test_invalid_processed_document_shape_is_rejected() -> None:
    with pytest.raises(ProcessedWaitingPeriodAuditError):
        audit_processed_waiting_period_candidates(
            [],  # type: ignore[arg-type]
            WaitingPeriodType.INITIAL,
            document_id=DOCUMENT_ID,
            processed_document_asset_id=ASSET_ID,
            source_document_sha256=SOURCE_SHA256,
        )


def test_loader_rejects_non_object_json(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    with pytest.raises(ProcessedWaitingPeriodAuditError):
        load_processed_document(path)
