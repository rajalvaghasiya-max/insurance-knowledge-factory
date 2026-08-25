from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.build_source_observation_from_acquisition import (
    build_source_observation_from_acquisition,
    select_download_observation,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_runner_writes_governed_observation_for_exact_download_item(tmp_path: Path) -> None:
    pdf = b"%PDF-1.7\nrunner fixture"
    pdf_rel = "archive/raw_pdf/test/policy.pdf"
    page_rel = "archive/raw_html/test/product.html"
    registration_rel = "knowledge/factory/registry_backed/test/generic_source_registration/policy_wording_registration.json"
    run_rel = "logs/pdf_download_runs/run.json"
    output_rel = "knowledge/factory/registry_backed/test/governance/source_observation.json"

    (tmp_path / pdf_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / pdf_rel).write_bytes(pdf)
    (tmp_path / page_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / page_rel).write_text("official product page", encoding="utf-8")
    page_sha = _sha((tmp_path / page_rel).read_bytes())

    _write_json(
        tmp_path / registration_rel,
        {
            "document": {
                "document_id": "test_policy_wording",
                "document_version_id": "docver_test_policy_wording",
                "document_type": "policy_wording",
                "content_sha256": _sha(pdf),
            }
        },
    )
    _write_json(
        tmp_path / run_rel,
        {
            "items": [
                {
                    "processed_at": "2026-08-25T22:00:00+05:30",
                    "insurer_id": "test_insurer",
                    "document_type": "policy_wording",
                    "url": "https://example.test/policy.pdf",
                    "url_key": "https://example.test/policy.pdf",
                    "source_page_url": "https://example.test/product",
                    "source_page_artifact_path": page_rel,
                    "source_page_artifact_sha256": page_sha,
                    "status": "downloaded",
                    "sha256": _sha(pdf),
                    "raw_pdf_relative_path": pdf_rel,
                    "http_status": 200,
                    "content_type": "application/pdf",
                    "observation_id": "pdfobs_exact_runner",
                }
            ]
        },
    )

    output = build_source_observation_from_acquisition(
        download_run_path=run_rel,
        observation_id="pdfobs_exact_runner",
        registration_path=registration_rel,
        output_path=output_rel,
        repository_root=tmp_path,
        version_signal="TESTHLIP00001V012626",
    )

    assert output == tmp_path / output_rel
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["observation_id"] == "pdfobs_exact_runner"
    assert record["byte_comparison"]["status"] == "byte_identical_observed"
    assert record["source_signals"]["version_signal"] == "TESTHLIP00001V012626"
    assert record["review_state"]["temporal_review_required"] is True
    assert "temporal_status" not in record


def test_selector_requires_exactly_one_observation_id() -> None:
    with pytest.raises(ValueError, match="found 0"):
        select_download_observation({"items": []}, "missing")

    duplicate = {
        "items": [
            {"observation_id": "same"},
            {"observation_id": "same"},
        ]
    }
    with pytest.raises(ValueError, match="found 2"):
        select_download_observation(duplicate, "same")


def test_selector_rejects_non_array_items() -> None:
    with pytest.raises(ValueError, match="items array"):
        select_download_observation({"items": {}}, "obs")
