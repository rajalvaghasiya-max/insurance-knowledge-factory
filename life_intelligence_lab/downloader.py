"""
life_intelligence_lab.downloader
=================================

Fetches the AMFI daily NAV flat file and writes it as an immutable raw
snapshot with retrieval metadata.

This module performs network I/O and file I/O ONLY. It never parses NAV
rows -- that is `parser.py`'s job, and it is deliberately kept in a
separate module (see ARCHITECTURE.md for why).

The HTTP transport is injectable via `fetch_fn`, so this module can be
fully unit-tested without live internet access: tests pass a fake
`fetch_fn`; only `default_http_fetch` (unused in tests) talks to the
network, using only the Python standard library.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Callable, Optional

from life_intelligence_lab.contracts import (
    ADAPTER_VERSION,
    RAW_SNAPSHOT_FIELD_ORDER,
    RawSnapshot,
    SNAPSHOT_STATUS_EMPTY_RESPONSE,
    SNAPSHOT_STATUS_HTTP_ERROR,
    SNAPSHOT_STATUS_OK,
    SNAPSHOT_STATUS_TIMEOUT,
)

AMFI_NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
DEFAULT_SOURCE_ID = "amfi_navall_txt"
DEFAULT_TIMEOUT_SECONDS = 30
RAW_MANIFEST_FILENAME = "manifest.json"
RAW_CONTENT_FILENAME = "raw.txt"


class DownloadFailedError(Exception):
    """
    Raised when a download attempt does not yield a usable raw snapshot
    (HTTP error, timeout, or empty response body). The failed attempt's
    manifest is still written to disk for audit purposes and is attached
    to this exception as `.snapshot`.
    """

    def __init__(self, message: str, snapshot: RawSnapshot):
        super().__init__(message)
        self.snapshot = snapshot


@dataclasses.dataclass(frozen=True)
class FetchResult:
    http_status: Optional[int]
    content_type: Optional[str]
    body_bytes: bytes
    error: Optional[str]


def default_http_fetch(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> FetchResult:
    """
    Real HTTP transport using only the standard library. Not exercised by
    the test suite (tests inject a fake `fetch_fn` instead), and not
    reachable from network-restricted sandboxes whose egress allowlist
    does not include amfiindia.com -- see PROTOTYPE_REPORT.md.
    """
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PolicyScna-LifeIntelligenceLab-Prototype/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            return FetchResult(
                http_status=getattr(response, "status", None),
                content_type=response.headers.get("Content-Type"),
                body_bytes=body,
                error=None,
            )
    except urllib.error.HTTPError as exc:
        return FetchResult(http_status=exc.code, content_type=None, body_bytes=b"", error=str(exc))
    except TimeoutError as exc:
        return FetchResult(http_status=None, content_type=None, body_bytes=b"", error=f"timeout: {exc}")
    except urllib.error.URLError as exc:
        reason = str(getattr(exc, "reason", exc))
        is_timeout = "timed out" in reason.lower()
        return FetchResult(
            http_status=None,
            content_type=None,
            body_bytes=b"",
            error=f"{'timeout' if is_timeout else 'url_error'}: {reason}",
        )


def _write_manifest(manifest_dir: str, snapshot: RawSnapshot) -> None:
    os.makedirs(manifest_dir, exist_ok=True)
    ordered = {field: getattr(snapshot, field) for field in RAW_SNAPSHOT_FIELD_ORDER}
    with open(os.path.join(manifest_dir, RAW_MANIFEST_FILENAME), "w", encoding="utf-8") as fh:
        json.dump(ordered, fh, indent=2, sort_keys=False)
        fh.write("\n")


def download_amfi_nav(
    output_root: str,
    url: str = AMFI_NAV_URL,
    fetch_fn: Callable[[str, int], FetchResult] = default_http_fetch,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    source_id: str = DEFAULT_SOURCE_ID,
    snapshot_id: Optional[str] = None,
) -> RawSnapshot:
    """
    Fetch `url` via `fetch_fn`, write an immutable raw snapshot under
    `output_root/<snapshot_id>/`, and return its RawSnapshot manifest.

    Raises DownloadFailedError (with the failed manifest attached) on
    HTTP error, timeout, or an empty response body -- a snapshot is
    never silently treated as valid just because *some* response arrived.
    """
    retrieval_timestamp = datetime.now(timezone.utc).isoformat()
    if snapshot_id is None:
        snapshot_id = "snap_" + retrieval_timestamp.replace(":", "").replace("+", "_")

    result = fetch_fn(url, timeout)
    manifest_dir = os.path.join(output_root, snapshot_id)

    if result.error is not None:
        status = SNAPSHOT_STATUS_TIMEOUT if "timeout" in result.error.lower() else SNAPSHOT_STATUS_HTTP_ERROR
        snapshot = RawSnapshot(
            snapshot_id=snapshot_id,
            source_id=source_id,
            source_url=url,
            retrieval_timestamp=retrieval_timestamp,
            http_status=result.http_status,
            content_type=result.content_type,
            raw_file_path=None,
            raw_sha256=None,
            adapter_version=ADAPTER_VERSION,
            status=status,
            warnings=[f"fetch_failed: {result.error}"],
        )
        _write_manifest(manifest_dir, snapshot)
        raise DownloadFailedError(f"AMFI NAV download failed: {result.error}", snapshot)

    if not result.body_bytes:
        snapshot = RawSnapshot(
            snapshot_id=snapshot_id,
            source_id=source_id,
            source_url=url,
            retrieval_timestamp=retrieval_timestamp,
            http_status=result.http_status,
            content_type=result.content_type,
            raw_file_path=None,
            raw_sha256=None,
            adapter_version=ADAPTER_VERSION,
            status=SNAPSHOT_STATUS_EMPTY_RESPONSE,
            warnings=["empty_response: source returned zero bytes"],
        )
        _write_manifest(manifest_dir, snapshot)
        raise DownloadFailedError("AMFI NAV download failed: empty response body", snapshot)

    os.makedirs(manifest_dir, exist_ok=True)
    raw_file_path = os.path.join(manifest_dir, RAW_CONTENT_FILENAME)
    with open(raw_file_path, "wb") as fh:
        fh.write(result.body_bytes)
    raw_sha256 = hashlib.sha256(result.body_bytes).hexdigest()

    snapshot = RawSnapshot(
        snapshot_id=snapshot_id,
        source_id=source_id,
        source_url=url,
        retrieval_timestamp=retrieval_timestamp,
        http_status=result.http_status,
        content_type=result.content_type,
        raw_file_path=raw_file_path,
        raw_sha256=raw_sha256,
        adapter_version=ADAPTER_VERSION,
        status=SNAPSHOT_STATUS_OK,
        warnings=[],
    )
    _write_manifest(manifest_dir, snapshot)
    return snapshot


def load_snapshot(manifest_dir: str) -> tuple[RawSnapshot, str]:
    """
    Load a previously-written snapshot's manifest and raw text content
    from disk, with no network access. Used by the parser/replay CLIs.
    """
    manifest_path = os.path.join(manifest_dir, RAW_MANIFEST_FILENAME)
    with open(manifest_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    snapshot = RawSnapshot(**data)

    if snapshot.raw_file_path is None:
        raise DownloadFailedError(
            f"Snapshot {snapshot.snapshot_id} has no raw content (status={snapshot.status})",
            snapshot,
        )
    # Read as raw bytes first (binary mode) so the hash check below is
    # against exactly the bytes that were written at download time -- text
    # mode would silently apply universal-newline translation (\r\n -> \n)
    # and could mask a real corruption, or falsely flag a clean CRLF file.
    with open(snapshot.raw_file_path, "rb") as fh:
        raw_bytes = fh.read()

    actual_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    if actual_sha256 != snapshot.raw_sha256:
        raise ValueError(
            f"hash_mismatch: raw file for snapshot {snapshot.snapshot_id} does not match "
            f"recorded raw_sha256 (expected {snapshot.raw_sha256}, got {actual_sha256})"
        )

    raw_text = raw_bytes.decode("utf-8")
    return snapshot, raw_text
