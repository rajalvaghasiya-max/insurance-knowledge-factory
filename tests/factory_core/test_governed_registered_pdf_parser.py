from __future__ import annotations

import hashlib
import json
from pathlib import Path

import fitz
import pytest

from factory_core.governance.governed_registered_pdf_parser import (
    GovernedRegisteredPdfParser,
    GovernedRegisteredPdfParserError,
)


def _write_pdf(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_registration(root: Path, sha256: str) -> str:
    path = root / "knowledge" / "registration.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "document": {
                    "document_id": "generic_policy_wording_v1",
                    "document_type": "policy_wording",
                    "content_sha256": sha256,
                    "storage_locator": "archive/raw_documents/policy.pdf",
                }
            }
        ),
        encoding="utf-8",
    )
    return "knowledge/registration.json"


def test_parses_registered_pdf_to_hash_addressed_generic_artifact(tmp_path: Path) -> None:
    sha256 = _write_pdf(tmp_path / "archive" / "raw_documents" / "policy.pdf", "Sum Insured Rs 500000")
    registration_path = _write_registration(tmp_path, sha256)

    result = GovernedRegisteredPdfParser(repository_root=tmp_path).parse(
        registration_path=registration_path,
        source_url="https://example.test/policy.pdf",
        entity_id="insurer:product",
        insurer_id="insurer",
    )

    assert result["status"] == "parsed"
    assert result["source_sha256"] == sha256
    assert result["page_count"] == 1
    output = tmp_path / result["output_path"]
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["sha256"] == sha256
    assert payload["source_document_id"] == f"sha256:{sha256}"
    assert payload["relative_archive_path"] == "archive/raw_documents/policy.pdf"
    assert payload["provenance_status"] == "governed_source_registration_sha256_verified"
    assert payload["pages"][0]["page_number"] == 1
    assert "500000" in payload["pages"][0]["text"]


def test_fails_closed_when_registered_hash_does_not_match_bytes(tmp_path: Path) -> None:
    _write_pdf(tmp_path / "archive" / "raw_documents" / "policy.pdf", "evidence")
    registration_path = _write_registration(tmp_path, "0" * 64)

    with pytest.raises(GovernedRegisteredPdfParserError, match="SHA-256 mismatch"):
        GovernedRegisteredPdfParser(repository_root=tmp_path).parse(
            registration_path=registration_path,
            source_url="https://example.test/policy.pdf",
            entity_id="insurer:product",
            insurer_id="insurer",
        )


def test_rejects_registered_path_outside_archive(tmp_path: Path) -> None:
    outside = tmp_path / "not_archive" / "policy.pdf"
    sha256 = _write_pdf(outside, "evidence")
    path = tmp_path / "knowledge" / "registration.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "document": {
                    "document_id": "generic_policy_wording_v1",
                    "document_type": "policy_wording",
                    "content_sha256": sha256,
                    "storage_locator": "not_archive/policy.pdf",
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(GovernedRegisteredPdfParserError, match="under archive"):
        GovernedRegisteredPdfParser(repository_root=tmp_path).parse(
            registration_path="knowledge/registration.json",
            source_url="https://example.test/policy.pdf",
            entity_id="insurer:product",
            insurer_id="insurer",
        )
