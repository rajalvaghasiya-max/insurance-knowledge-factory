from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from factory_core.governance.document_currentness_evidence import (
    DocumentCurrentnessEvidenceError,
    DocumentCurrentnessEvidenceRecord,
)
from scripts.build_source_observation_from_acquisition import (
    build_source_observation_from_acquisition,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _registration(root: Path, registered_sha: str) -> str:
    relative = (
        "knowledge/factory/registry_backed/test_product/"
        "generic_source_registration/policy_wording_registration.json"
    )
    _write_json(
        root / relative,
        {
            "document": {
                "document_id": "test_product_policy_wording",
                "document_version_id": "docver_test_product_policy_wording",
                "document_type": "policy_wording",
                "content_sha256": registered_sha,
            }
        },
    )
    return relative


def _write_acquisition_fixture(
    root: Path,
    *,
    observed_bytes: bytes,
    observation_id: str,
) -> tuple[str, str, str]:
    pdf_rel = "archive/raw_pdf/test_product/policy.pdf"
    page_rel = "archive/raw_html/test_product/product.html"
    run_rel = "logs/pdf_download_runs/test_product_run.json"

    (root / pdf_rel).parent.mkdir(parents=True, exist_ok=True)
    (root / pdf_rel).write_bytes(observed_bytes)
    (root / page_rel).parent.mkdir(parents=True, exist_ok=True)
    (root / page_rel).write_text(
        "<html><a href='https://example.test/policy.pdf'>Policy Wording</a></html>",
        encoding="utf-8",
    )
    page_sha = _sha((root / page_rel).read_bytes())

    _write_json(
        root / run_rel,
        {
            "items": [
                {
                    "processed_at": "2026-08-25T22:10:00+05:30",
                    "insurer_id": "test_insurer",
                    "document_type": "policy_wording",
                    "url": "https://example.test/policy.pdf",
                    "url_key": "https://example.test/policy.pdf",
                    "source_page_url": "https://example.test/product",
                    "source_page_artifact_path": page_rel,
                    "source_page_artifact_sha256": page_sha,
                    "status": "downloaded",
                    "sha256": _sha(observed_bytes),
                    "raw_pdf_relative_path": pdf_rel,
                    "http_status": 200,
                    "content_type": "application/pdf",
                    "observation_id": observation_id,
                }
            ]
        },
    )
    return run_rel, page_rel, pdf_rel


def _currentness_spec(registration_rel: str, observation_rel: str, page_rel: str) -> dict:
    return {
        "schema_version": "1.0",
        "record_type": "document_currentness_evidence_record_v1",
        "reviewed_by_human": True,
        "registered_document": {"registration_path": registration_rel},
        "source_observation": {"observation_record_path": observation_rel},
        "evidence_items": [
            {
                "evidence_type": "official_product_page_document_link",
                "evidence_status": "supports_currentness_review",
                "verification": "retained_official_html_manual_review",
                "observed_text": "Official product page links the observed policy wording.",
                "evidence_reference": page_rel,
                "linked_document_url": "https://example.test/policy.pdf",
                "link_label": "Policy Wording",
            }
        ],
        "reviewed_at": "2026-08-25T22:12:00+05:30",
        "review_rationale": (
            "C3 integration fixture proving acquisition observations feed the existing "
            "reviewed currentness evidence gate."
        ),
    }


def test_acquisition_observation_is_accepted_by_existing_currentness_evidence_gate(
    tmp_path: Path,
) -> None:
    observed = b"%PDF-1.7\nbyte-identical-currentness-integration"
    registration_rel = _registration(tmp_path, _sha(observed))
    run_rel, page_rel, _pdf_rel = _write_acquisition_fixture(
        tmp_path,
        observed_bytes=observed,
        observation_id="pdfobs_currentness_handoff",
    )
    observation_rel = (
        "knowledge/factory/registry_backed/test_product/governance/"
        "source_observation.json"
    )

    observation_path = build_source_observation_from_acquisition(
        download_run_path=run_rel,
        observation_id="pdfobs_currentness_handoff",
        registration_path=registration_rel,
        output_path=observation_rel,
        repository_root=tmp_path,
        version_signal="TESTHLIP00001V012626",
    )
    observation = json.loads(observation_path.read_text(encoding="utf-8"))
    assert observation["byte_comparison"]["status"] == "byte_identical_observed"
    assert observation["record_status"] == "source_observation_recorded_review_required"

    evidence = DocumentCurrentnessEvidenceRecord().build(
        spec=_currentness_spec(registration_rel, observation_rel, page_rel),
        repository_root=tmp_path,
        recorded_at="2026-08-25T22:13:00+05:30",
    ).record

    assert evidence["record_type"] == "document_currentness_evidence_record_v1"
    assert evidence["record_status"] == "currentness_evidence_recorded_not_decided"
    assert evidence["positive_currentness_evidence_count"] == 1
    assert evidence["currentness_evidence_conclusion"] == (
        "sufficient_for_current_observed_review"
    )
    assert evidence["source_observation"]["observation_id"] == (
        "pdfobs_currentness_handoff"
    )
    assert evidence["source_observation"]["byte_comparison_status"] == (
        "byte_identical_observed"
    )
    assert "temporal_status" not in evidence
    assert "current_entitlement_publication_eligibility" not in evidence


def test_changed_acquisition_bytes_are_rejected_by_currentness_evidence_gate(
    tmp_path: Path,
) -> None:
    registered = b"%PDF-1.7\nregistered-version"
    observed = b"%PDF-1.7\nnewly-observed-version"
    registration_rel = _registration(tmp_path, _sha(registered))
    run_rel, page_rel, _pdf_rel = _write_acquisition_fixture(
        tmp_path,
        observed_bytes=observed,
        observation_id="pdfobs_changed_currentness_handoff",
    )
    observation_rel = (
        "knowledge/factory/registry_backed/test_product/governance/"
        "changed_source_observation.json"
    )

    observation_path = build_source_observation_from_acquisition(
        download_run_path=run_rel,
        observation_id="pdfobs_changed_currentness_handoff",
        registration_path=registration_rel,
        output_path=observation_rel,
        repository_root=tmp_path,
    )
    observation = json.loads(observation_path.read_text(encoding="utf-8"))
    assert observation["byte_comparison"]["status"] == "bytes_changed_observed"

    with pytest.raises(
        DocumentCurrentnessEvidenceError,
        match="byte_identical_observed",
    ):
        DocumentCurrentnessEvidenceRecord().build(
            spec=_currentness_spec(registration_rel, observation_rel, page_rel),
            repository_root=tmp_path,
            recorded_at="2026-08-25T22:13:00+05:30",
        )
