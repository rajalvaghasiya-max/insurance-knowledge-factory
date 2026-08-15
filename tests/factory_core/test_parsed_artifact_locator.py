from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory_core.governance.parsed_artifact_locator import (
    ParsedArtifactLocator,
    ParsedArtifactLocatorError,
)


SHA = "a" * 64


def _write(root: Path, relative: str, payload: object) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _parsed(sha: str = SHA) -> dict:
    return {
        "entity_id": "insurer:product",
        "document_type": "policy_wording",
        "source_document_id": sha,
        "sha256": sha,
        "provenance_status": "retained",
        "pages": [
            {"page_number": 1, "text": "Rs. 5,00,000 Sum Insured"},
            {"page_number": 2, "text": ""},
        ],
    }


def test_locates_parsed_artifact_by_sha_and_shape(tmp_path: Path):
    _write(tmp_path, "archive/parsed/a.json", _parsed())
    _write(tmp_path, "archive/parsed/wrong.json", _parsed("b" * 64))
    _write(tmp_path, "knowledge/not_parse.json", {"sha256": SHA, "pages": "not-a-list"})

    result = ParsedArtifactLocator.locate(repository_root=tmp_path, source_sha256=SHA).manifest

    assert result["locator_status"] == "located"
    assert result["match_count"] == 1
    assert result["matches"][0]["path"] == "archive/parsed/a.json"
    assert result["matches"][0]["page_count"] == 2
    assert result["matches"][0]["valid_text_page_count"] == 2


def test_locates_canonical_processed_pdf_parse_by_default(tmp_path: Path):
    _write(tmp_path, f"processed/pdf_parse/{SHA}.json", _parsed())

    result = ParsedArtifactLocator.locate(repository_root=tmp_path, source_sha256=SHA).manifest

    assert "processed" in result["search_roots"]
    assert result["locator_status"] == "located"
    assert result["match_count"] == 1
    assert result["matches"][0]["path"] == f"processed/pdf_parse/{SHA}.json"


def test_missing_sha_is_explicit_not_found(tmp_path: Path):
    (tmp_path / "archive").mkdir()
    result = ParsedArtifactLocator.locate(repository_root=tmp_path, source_sha256=SHA).manifest
    assert result["locator_status"] == "not_found"
    assert result["matches"] == []


def test_invalid_json_is_skipped_without_false_match(tmp_path: Path):
    path = tmp_path / "archive/bad.json"
    path.parent.mkdir(parents=True)
    path.write_text("{bad", encoding="utf-8")
    result = ParsedArtifactLocator.locate(repository_root=tmp_path, source_sha256=SHA).manifest
    assert result["match_count"] == 0
    assert result["skipped_invalid_json"] == 1


def test_path_traversal_root_fails_closed(tmp_path: Path):
    with pytest.raises(ParsedArtifactLocatorError, match="safe repository-relative"):
        ParsedArtifactLocator.locate(
            repository_root=tmp_path,
            source_sha256=SHA,
            search_roots=["../outside"],
        )


def test_invalid_sha_fails_closed(tmp_path: Path):
    with pytest.raises(ParsedArtifactLocatorError, match="SHA-256"):
        ParsedArtifactLocator.locate(repository_root=tmp_path, source_sha256="not-a-sha")
