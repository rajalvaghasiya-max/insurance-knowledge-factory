import hashlib
import os

import pytest

from life_intelligence_lab.contracts import ADAPTER_VERSION, RawSnapshot

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures")


def _read_fixture(name: str) -> str:
    path = os.path.join(FIXTURES_DIR, name)
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def make_snapshot(raw_text: str, snapshot_id: str = "test_snapshot") -> RawSnapshot:
    """Build an in-memory RawSnapshot matching the given raw text, without
    touching disk -- used by parser-level unit tests that don't need a
    real file on disk."""
    sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    return RawSnapshot(
        snapshot_id=snapshot_id,
        source_id="amfi_navall_txt",
        source_url="https://www.amfiindia.com/spages/NAVAll.txt",
        retrieval_timestamp="2026-07-26T09:15:00+00:00",
        http_status=200,
        content_type="text/plain",
        raw_file_path=None,
        raw_sha256=sha256,
        adapter_version=ADAPTER_VERSION,
        status="ok",
        warnings=[],
    )


@pytest.fixture
def valid_fixture_text() -> str:
    return _read_fixture("sample_amfi_nav_valid.txt")


@pytest.fixture
def errors_fixture_text() -> str:
    return _read_fixture("sample_amfi_nav_with_errors.txt")


@pytest.fixture
def valid_snapshot(valid_fixture_text) -> RawSnapshot:
    return make_snapshot(valid_fixture_text, snapshot_id="valid_snapshot")


@pytest.fixture
def errors_snapshot(errors_fixture_text) -> RawSnapshot:
    return make_snapshot(errors_fixture_text, snapshot_id="errors_snapshot")
