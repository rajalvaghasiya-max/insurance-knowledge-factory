import hashlib
import inspect
import json
import os

import pytest

from life_intelligence_lab.downloader import (
    DownloadFailedError,
    FetchResult,
    download_amfi_nav,
    load_snapshot,
)


def _fake_fetch_ok(body: bytes):
    def fetch_fn(url, timeout):
        return FetchResult(http_status=200, content_type="text/plain", body_bytes=body, error=None)
    return fetch_fn


def _fake_fetch_http_error(status: int, message: str):
    def fetch_fn(url, timeout):
        return FetchResult(http_status=status, content_type=None, body_bytes=b"", error=f"HTTP Error {status}: {message}")
    return fetch_fn


def _fake_fetch_timeout():
    def fetch_fn(url, timeout):
        return FetchResult(http_status=None, content_type=None, body_bytes=b"", error="timeout: read timed out")
    return fetch_fn


def _fake_fetch_empty():
    def fetch_fn(url, timeout):
        return FetchResult(http_status=200, content_type="text/plain", body_bytes=b"", error=None)
    return fetch_fn


def test_successful_download_writes_snapshot_and_hash(tmp_path):
    body = b"Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date\n"
    snapshot = download_amfi_nav(
        output_root=str(tmp_path), fetch_fn=_fake_fetch_ok(body), snapshot_id="snap_a"
    )
    assert snapshot.status == "ok"
    assert snapshot.raw_sha256 == hashlib.sha256(body).hexdigest()
    assert os.path.exists(snapshot.raw_file_path)
    with open(snapshot.raw_file_path, "rb") as fh:
        assert fh.read() == body
    manifest_path = os.path.join(str(tmp_path), "snap_a", "manifest.json")
    assert os.path.exists(manifest_path)
    with open(manifest_path) as fh:
        manifest = json.load(fh)
    assert manifest["raw_sha256"] == snapshot.raw_sha256


# --- 13. HTTP failure --------------------------------------------------------

def test_http_error_raises_and_writes_failure_manifest(tmp_path):
    with pytest.raises(DownloadFailedError) as excinfo:
        download_amfi_nav(
            output_root=str(tmp_path),
            fetch_fn=_fake_fetch_http_error(503, "Service Unavailable"),
            snapshot_id="snap_http_fail",
        )
    snapshot = excinfo.value.snapshot
    assert snapshot.status == "http_error"
    assert snapshot.raw_file_path is None
    manifest_path = os.path.join(str(tmp_path), "snap_http_fail", "manifest.json")
    assert os.path.exists(manifest_path)  # failure is still recorded for audit


# --- 14. Timeout handling -----------------------------------------------------

def test_timeout_raises_and_is_distinguished_from_http_error(tmp_path):
    with pytest.raises(DownloadFailedError) as excinfo:
        download_amfi_nav(
            output_root=str(tmp_path), fetch_fn=_fake_fetch_timeout(), snapshot_id="snap_timeout"
        )
    assert excinfo.value.snapshot.status == "timeout"


def test_empty_response_is_rejected_not_treated_as_valid(tmp_path):
    with pytest.raises(DownloadFailedError) as excinfo:
        download_amfi_nav(
            output_root=str(tmp_path), fetch_fn=_fake_fetch_empty(), snapshot_id="snap_empty"
        )
    assert excinfo.value.snapshot.status == "empty_response"
    assert excinfo.value.snapshot.raw_file_path is None


def test_load_snapshot_roundtrips_and_verifies_hash(tmp_path):
    body = b"118551;INF209K01UN8;-;Test Fund;100.0000;25-Jul-2026\n"
    snapshot = download_amfi_nav(output_root=str(tmp_path), fetch_fn=_fake_fetch_ok(body), snapshot_id="snap_rt")
    loaded_snapshot, raw_text = load_snapshot(os.path.join(str(tmp_path), "snap_rt"))
    assert loaded_snapshot.snapshot_id == snapshot.snapshot_id
    assert raw_text == body.decode("utf-8")


def test_load_snapshot_detects_hash_mismatch(tmp_path):
    body = b"118551;INF209K01UN8;-;Test Fund;100.0000;25-Jul-2026\n"
    download_amfi_nav(output_root=str(tmp_path), fetch_fn=_fake_fetch_ok(body), snapshot_id="snap_corrupt")
    raw_path = os.path.join(str(tmp_path), "snap_corrupt", "raw.txt")
    with open(raw_path, "ab") as fh:
        fh.write(b"TAMPERED")
    with pytest.raises(ValueError, match="hash_mismatch"):
        load_snapshot(os.path.join(str(tmp_path), "snap_corrupt"))


# --- 12. Downloader/parser separation -----------------------------------------

def test_downloader_module_does_not_import_parser():
    import life_intelligence_lab.downloader as downloader_module

    source = inspect.getsource(downloader_module)
    assert "import life_intelligence_lab.parser" not in source
    assert "from life_intelligence_lab.parser" not in source
    assert "from life_intelligence_lab import parser" not in source


def test_downloader_does_not_parse_nav_rows(tmp_path):
    # The downloader's return value (RawSnapshot) must never carry any
    # parsed NAV field -- it only ever describes the raw download, never
    # its content's meaning.
    body = b"118551;INF209K01UN8;-;Test Fund;100.0000;25-Jul-2026\n"
    snapshot = download_amfi_nav(output_root=str(tmp_path), fetch_fn=_fake_fetch_ok(body), snapshot_id="snap_sep")
    snapshot_fields = set(vars(snapshot).keys())
    assert "nav_value" not in snapshot_fields
    assert "amfi_scheme_code" not in snapshot_fields
