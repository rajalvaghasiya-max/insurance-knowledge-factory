from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from factory_core.governance.source_hash_locator import SourceHashLocator, SourceHashLocatorError


def _write(root: Path, relative: str, content: bytes) -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def test_locates_matching_source_under_default_roots(tmp_path: Path):
    expected = _write(tmp_path, "archive/raw_pdf/example/policy.pdf", b"policy-bytes")
    result = SourceHashLocator.locate(repository_root=tmp_path, sha256_values=[expected])
    assert [row.relative_path for row in result[expected]] == ["archive/raw_pdf/example/policy.pdf"]


def test_reports_empty_when_hash_is_not_retained(tmp_path: Path):
    (tmp_path / "archive").mkdir()
    digest = hashlib.sha256(b"missing").hexdigest()
    result = SourceHashLocator.locate(repository_root=tmp_path, sha256_values=[digest])
    assert result[digest] == []


def test_search_roots_can_be_scoped(tmp_path: Path):
    digest = _write(tmp_path, "other/source.bin", b"bytes")
    result = SourceHashLocator.locate(
        repository_root=tmp_path, sha256_values=[digest], search_roots=["other"]
    )
    assert result[digest][0].relative_path == "other/source.bin"


def test_rejects_invalid_hash(tmp_path: Path):
    with pytest.raises(SourceHashLocatorError, match="64-character"):
        SourceHashLocator.locate(repository_root=tmp_path, sha256_values=["abc"])


def test_rejects_unsafe_search_root(tmp_path: Path):
    digest = hashlib.sha256(b"x").hexdigest()
    with pytest.raises(SourceHashLocatorError, match="safe repository-relative"):
        SourceHashLocator.locate(
            repository_root=tmp_path, sha256_values=[digest], search_roots=["../outside"]
        )
