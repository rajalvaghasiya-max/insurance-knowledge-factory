"""C3 — bridge durable acquisition results into governed source observations.

This module adapts one PDFDownloadAgent result into the existing
SourceObservationRecord contract. It does not decide currentness, document
identity, publication eligibility, or semantic truth.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from factory_core.governance.source_observation import (
    SourceObservationError,
    SourceObservationRecord,
    SourceObservationResult,
)


class AcquisitionSourceObservationError(ValueError):
    """Raised when an acquisition result cannot be bound safely to governance."""


_SUCCESS_STATUSES = frozenset({"downloaded", "new_version_downloaded", "unchanged"})
_ALLOWED_STATUSES = _SUCCESS_STATUSES | {"failed"}


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise AcquisitionSourceObservationError(f"{label} must be a JSON object")
    return value


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AcquisitionSourceObservationError(f"{label} must be a non-empty string")
    return value.strip()


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _nonempty(value, label)


def _safe_relative_path(value: object, label: str) -> str:
    raw = _nonempty(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise AcquisitionSourceObservationError(
            f"{label} must be a safe repository-relative path"
        )
    return path.as_posix()


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_sha256(value: object, label: str) -> str:
    raw = _nonempty(value, label).lower()
    if len(raw) != 64 or any(character not in "0123456789abcdef" for character in raw):
        raise AcquisitionSourceObservationError(f"{label} must be a SHA-256 hex digest")
    return raw


def _resolve_repo_file(root: Path, relative_path: str, label: str) -> Path:
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise AcquisitionSourceObservationError(
            f"{label} must remain under repository_root"
        ) from exc
    if not path.is_file():
        raise AcquisitionSourceObservationError(f"{label} was not found: {relative_path}")
    return path


def _derived_observation_id(url_key: str, processed_at: str) -> str:
    digest = sha256(f"{url_key}|{processed_at}".encode("utf-8")).hexdigest()[:20]
    return f"acqobs_{digest}"


class AcquisitionSourceObservationBridge:
    """Convert a durable downloader result into SourceObservationRecord input."""

    def build(
        self,
        *,
        acquisition_result: Mapping[str, Any],
        registration_path: str,
        repository_root: str | Path,
        source_signals: Mapping[str, Any] | None = None,
        recorded_at: str | None = None,
    ) -> SourceObservationResult:
        result = _mapping(acquisition_result, "acquisition_result")
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"repository_root was not found: {root}")

        status = _nonempty(result.get("status"), "acquisition_result.status")
        if status not in _ALLOWED_STATUSES:
            raise AcquisitionSourceObservationError(
                "acquisition_result.status must be downloaded, new_version_downloaded, unchanged, or failed"
            )

        registered_path = _safe_relative_path(registration_path, "registration_path")
        source_url = _nonempty(result.get("url"), "acquisition_result.url")
        source_url_key = _optional_text(result.get("url_key"), "acquisition_result.url_key") or source_url
        processed_at = _nonempty(
            result.get("processed_at"), "acquisition_result.processed_at"
        )
        observation_id = (
            _optional_text(result.get("observation_id"), "acquisition_result.observation_id")
            or _derived_observation_id(source_url_key, processed_at)
        )

        source_page_path = self._validated_source_page_path(result=result, root=root)

        observation: dict[str, Any] = {
            "retrieval_status": "succeeded" if status in _SUCCESS_STATUSES else "failed",
            "source_url": source_url,
            "source_url_key": source_url_key,
            "source_page_url": result.get("source_page_url"),
            "source_page_artifact_path": source_page_path,
            "observed_at": processed_at,
            "http_status": result.get("http_status"),
            "content_type": result.get("content_type"),
            "capture_strategy": result.get("capture_strategy"),
        }

        if status in _SUCCESS_STATUSES:
            pdf_path = _safe_relative_path(
                result.get("raw_pdf_relative_path"),
                "acquisition_result.raw_pdf_relative_path",
            )
            pdf_file = _resolve_repo_file(root, pdf_path, "acquisition_result.raw_pdf_relative_path")
            actual_sha = _sha256_file(pdf_file)
            claimed_sha = _require_sha256(result.get("sha256"), "acquisition_result.sha256")
            if claimed_sha != actual_sha:
                raise AcquisitionSourceObservationError(
                    "acquisition_result.sha256 does not match raw_pdf_relative_path bytes"
                )
            observation["observed_pdf_path"] = pdf_path
            observation["observed_pdf_sha256"] = claimed_sha
        else:
            forbidden = ("raw_pdf_relative_path", "sha256")
            if any(result.get(field) is not None for field in forbidden):
                raise AcquisitionSourceObservationError(
                    "failed acquisition results must not claim observed PDF path or SHA-256"
                )

        signals = dict(source_signals or {})
        spec = {
            "schema_version": "1.0",
            "record_type": "source_observation_record_v1",
            "observation_id": observation_id,
            "registered_document": {"registration_path": registered_path},
            "observation": observation,
            "source_signals": {
                "source_issued_label": signals.get("source_issued_label"),
                "effective_date_signal": signals.get("effective_date_signal"),
                "version_signal": signals.get("version_signal"),
            },
        }

        try:
            return SourceObservationRecord().build(
                spec=spec,
                repository_root=root,
                recorded_at=recorded_at,
            )
        except SourceObservationError as exc:
            raise AcquisitionSourceObservationError(str(exc)) from exc

    def _validated_source_page_path(
        self,
        *,
        result: Mapping[str, Any],
        root: Path,
    ) -> str | None:
        raw_path = result.get("source_page_artifact_path")
        if raw_path is None:
            return None
        relative_path = _safe_relative_path(
            raw_path, "acquisition_result.source_page_artifact_path"
        )
        page_file = _resolve_repo_file(
            root,
            relative_path,
            "acquisition_result.source_page_artifact_path",
        )
        supplied_sha = result.get("source_page_artifact_sha256")
        if supplied_sha is not None:
            claimed_sha = _require_sha256(
                supplied_sha,
                "acquisition_result.source_page_artifact_sha256",
            )
            if _sha256_file(page_file) != claimed_sha:
                raise AcquisitionSourceObservationError(
                    "acquisition_result.source_page_artifact_sha256 does not match retained source page bytes"
                )
        return relative_path
