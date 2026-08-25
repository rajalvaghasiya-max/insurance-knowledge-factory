from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from factory_core.governance.acquisition_source_observation import (
    AcquisitionSourceObservationBridge,
    AcquisitionSourceObservationError,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _registration(root: Path, content_sha: str) -> str:
    relative = "knowledge/factory/registry_backed/test_product/generic_source_registration/policy_wording_registration.json"
    _write_json(
        root / relative,
        {
            "document": {
                "document_id": "test_policy_wording",
                "document_version_id": "docver_test_policy_wording",
                "document_type": "policy_wording",
                "content_sha256": content_sha,
            }
        },
    )
    return relative


def _page(root: Path) -> tuple[str, str]:
    relative = "archive/raw_html/test_product/product.html"
    data = b"<html><a href='policy.pdf'>Policy Wording</a></html>"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return relative, _sha(data)


def _download_result(
    *,
    pdf_path: str | None,
    pdf_sha: str | None,
    page_path: str,
    page_sha: str,
    status: str = "downloaded",
) -> dict:
    return {
        "processed_at": "2026-08-25T21:50:00+05:30",
        "insurer_id": "test_insurer",
        "document_type": "policy_wording",
        "url": "https://example.test/policy.pdf",
        "url_key": "https://example.test/policy.pdf",
        "source_page_url": "https://example.test/product",
        "source_page_artifact_path": page_path,
        "source_page_artifact_sha256": page_sha,
        "status": status,
        "sha256": pdf_sha,
        "raw_pdf_relative_path": pdf_path,
        "http_status": 200 if status != "failed" else 403,
        "content_type": "application/pdf" if status != "failed" else "text/html",
        "observation_id": "pdfobs_test_bridge",
    }


def test_byte_identical_download_becomes_review_required_source_observation(tmp_path: Path) -> None:
    pdf_bytes = b"%PDF-1.7\ncurrent bytes"
    pdf_rel = "archive/raw_pdf/test_product/policy.pdf"
    (tmp_path / pdf_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / pdf_rel).write_bytes(pdf_bytes)
    registration = _registration(tmp_path, _sha(pdf_bytes))
    page_rel, page_sha = _page(tmp_path)

    result = AcquisitionSourceObservationBridge().build(
        acquisition_result=_download_result(
            pdf_path=pdf_rel,
            pdf_sha=_sha(pdf_bytes),
            page_path=page_rel,
            page_sha=page_sha,
        ),
        registration_path=registration,
        repository_root=tmp_path,
        source_signals={"version_signal": "TESTHLIP00001V012626"},
        recorded_at="2026-08-25T21:51:00+05:30",
    ).record

    assert result["record_type"] == "source_observation_record_v1"
    assert result["record_status"] == "source_observation_recorded_review_required"
    assert result["byte_comparison"]["status"] == "byte_identical_observed"
    assert result["official_observation"]["observed_pdf"]["content_sha256"] == _sha(pdf_bytes)
    assert result["official_observation"]["source_page_artifact"]["content_sha256"] == page_sha
    assert result["source_signals"]["version_signal"] == "TESTHLIP00001V012626"
    assert result["review_state"]["temporal_review_required"] is True
    assert result["review_state"]["reviewed_by_human"] is False
    assert "temporal_status" not in result
    assert "current_entitlement_publication_eligibility" not in result


def test_changed_download_is_recorded_as_changed_not_current(tmp_path: Path) -> None:
    registered = b"%PDF-1.7\nregistered"
    observed = b"%PDF-1.7\nchanged"
    pdf_rel = "archive/raw_pdf/test_product/policy.pdf"
    (tmp_path / pdf_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / pdf_rel).write_bytes(observed)
    registration = _registration(tmp_path, _sha(registered))
    page_rel, page_sha = _page(tmp_path)

    result = AcquisitionSourceObservationBridge().build(
        acquisition_result=_download_result(
            pdf_path=pdf_rel,
            pdf_sha=_sha(observed),
            page_path=page_rel,
            page_sha=page_sha,
            status="new_version_downloaded",
        ),
        registration_path=registration,
        repository_root=tmp_path,
    ).record

    assert result["byte_comparison"]["status"] == "bytes_changed_observed"
    assert result["review_state"]["temporal_review_required"] is True
    assert "temporal_status" not in result


def test_failed_acquisition_becomes_observation_failed_without_fake_hash(tmp_path: Path) -> None:
    registration = _registration(tmp_path, _sha(b"registered"))
    page_rel, page_sha = _page(tmp_path)
    failed = _download_result(
        pdf_path=None,
        pdf_sha=None,
        page_path=page_rel,
        page_sha=page_sha,
        status="failed",
    )

    result = AcquisitionSourceObservationBridge().build(
        acquisition_result=failed,
        registration_path=registration,
        repository_root=tmp_path,
    ).record

    assert result["official_observation"]["retrieval_status"] == "failed"
    assert result["official_observation"]["observed_pdf"] is None
    assert result["byte_comparison"]["status"] == "observation_failed"
    assert result["byte_comparison"]["observed_document_sha256"] is None


def test_claimed_pdf_hash_must_match_acquired_bytes(tmp_path: Path) -> None:
    pdf_bytes = b"%PDF-1.7\nreal bytes"
    pdf_rel = "archive/raw_pdf/test_product/policy.pdf"
    (tmp_path / pdf_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / pdf_rel).write_bytes(pdf_bytes)
    registration = _registration(tmp_path, _sha(pdf_bytes))
    page_rel, page_sha = _page(tmp_path)

    with pytest.raises(AcquisitionSourceObservationError, match="sha256 does not match"):
        AcquisitionSourceObservationBridge().build(
            acquisition_result=_download_result(
                pdf_path=pdf_rel,
                pdf_sha="0" * 64,
                page_path=page_rel,
                page_sha=page_sha,
            ),
            registration_path=registration,
            repository_root=tmp_path,
        )


def test_retained_source_page_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    pdf_bytes = b"%PDF-1.7\nreal bytes"
    pdf_rel = "archive/raw_pdf/test_product/policy.pdf"
    (tmp_path / pdf_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / pdf_rel).write_bytes(pdf_bytes)
    registration = _registration(tmp_path, _sha(pdf_bytes))
    page_rel, _page_sha = _page(tmp_path)

    with pytest.raises(
        AcquisitionSourceObservationError,
        match="source_page_artifact_sha256 does not match",
    ):
        AcquisitionSourceObservationBridge().build(
            acquisition_result=_download_result(
                pdf_path=pdf_rel,
                pdf_sha=_sha(pdf_bytes),
                page_path=page_rel,
                page_sha="f" * 64,
            ),
            registration_path=registration,
            repository_root=tmp_path,
        )


def test_failed_acquisition_cannot_claim_pdf_artifact(tmp_path: Path) -> None:
    registration = _registration(tmp_path, _sha(b"registered"))
    page_rel, page_sha = _page(tmp_path)

    with pytest.raises(
        AcquisitionSourceObservationError,
        match="failed acquisition results must not claim",
    ):
        AcquisitionSourceObservationBridge().build(
            acquisition_result=_download_result(
                pdf_path="archive/raw_pdf/test_product/fake.pdf",
                pdf_sha="a" * 64,
                page_path=page_rel,
                page_sha=page_sha,
                status="failed",
            ),
            registration_path=registration,
            repository_root=tmp_path,
        )
