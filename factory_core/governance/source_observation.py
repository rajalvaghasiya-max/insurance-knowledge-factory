"""P1.5d-0 — governed source observation record contract.

Creates a durable, non-mutating record that binds one timestamped official-source
observation to one already-registered immutable document version.  It deliberately
does not decide whether a product document is currently applicable, replace an
identity overlay, or publish insurance facts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse


class SourceObservationError(ValueError):
    """Raised when a source observation cannot be recorded truthfully."""


_ALLOWED_RETRIEVAL_STATUSES = frozenset({"succeeded", "failed"})
_ALLOWED_COMPARISON_STATUSES = frozenset({
    "byte_identical_observed",
    "bytes_changed_observed",
    "observation_failed",
})


@dataclass(frozen=True)
class SourceObservationResult:
    record: Mapping[str, Any]


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise SourceObservationError(f"{label} must be a JSON object")
    return value


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceObservationError(f"{label} must be a non-empty string")
    return value.strip()


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _nonempty(value, label)


def _safe_relative_path(value: object, label: str) -> str:
    raw = _nonempty(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise SourceObservationError(f"{label} must be a safe repository-relative path")
    return path.as_posix()


def _resolve_file(root: Path, relative_path: str, label: str) -> Path:
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise SourceObservationError(f"{label} must remain under repository_root") from exc
    if not path.is_file():
        raise SourceObservationError(f"{label} was not found: {relative_path}")
    return path


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(root: Path, relative_path: str, label: str) -> Mapping[str, Any]:
    path = _resolve_file(root, relative_path, label)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceObservationError(f"{label} is not valid JSON: {relative_path}") from exc
    return _mapping(payload, label)


def _require_http_url(value: object, label: str) -> str:
    raw = _nonempty(value, label)
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SourceObservationError(f"{label} must be an absolute http(s) URL")
    return raw


def _require_iso_datetime(value: object, label: str) -> str:
    raw = _nonempty(value, label)
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceObservationError(f"{label} must be an ISO-8601 timestamp") from exc
    return raw


def _optional_sha256(value: object, label: str) -> str | None:
    if value is None:
        return None
    raw = _nonempty(value, label).lower()
    if len(raw) != 64 or any(character not in "0123456789abcdef" for character in raw):
        raise SourceObservationError(f"{label} must be a lowercase SHA-256 hex digest")
    return raw


class SourceObservationRecord:
    """Builds a durable source observation record without changing product truth."""

    def build_from_spec_file(
        self,
        *,
        spec_path: str | Path,
        repository_root: str | Path,
    ) -> SourceObservationResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Source observation specification was not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SourceObservationError(f"Invalid source observation specification JSON: {path}") from exc
        return self.build(spec=_mapping(payload, "source_observation_spec"), repository_root=repository_root)

    def build(
        self,
        *,
        spec: Mapping[str, Any],
        repository_root: str | Path,
        recorded_at: str | None = None,
    ) -> SourceObservationResult:
        spec = _mapping(spec, "source_observation_spec")
        if spec.get("schema_version") != "1.0":
            raise SourceObservationError("source_observation_spec.schema_version must be 1.0")
        if spec.get("record_type") != "source_observation_record_v1":
            raise SourceObservationError(
                "source_observation_spec.record_type must be source_observation_record_v1"
            )

        root = Path(repository_root)
        if not root.is_dir():
            raise FileNotFoundError(f"repository_root was not found: {root}")

        observation_id = _nonempty(spec.get("observation_id"), "source_observation_spec.observation_id")
        registration_path = _safe_relative_path(
            _mapping(spec.get("registered_document"), "registered_document").get("registration_path"),
            "registered_document.registration_path",
        )
        registration = _load_json(root, registration_path, "registered_document.registration")
        document = _mapping(registration.get("document"), "registered_document.registration.document")
        document_id = _nonempty(document.get("document_id"), "registered_document.document_id")
        document_version_id = _nonempty(
            document.get("document_version_id"), "registered_document.document_version_id"
        )
        registered_sha256 = _optional_sha256(
            document.get("content_sha256"), "registered_document.content_sha256"
        )
        if registered_sha256 is None:  # defensive, for type clarity
            raise SourceObservationError("registered_document.content_sha256 is required")

        observation = _mapping(spec.get("observation"), "observation")
        retrieval_status = _nonempty(observation.get("retrieval_status"), "observation.retrieval_status")
        if retrieval_status not in _ALLOWED_RETRIEVAL_STATUSES:
            raise SourceObservationError(
                f"observation.retrieval_status must be one of: {', '.join(sorted(_ALLOWED_RETRIEVAL_STATUSES))}"
            )

        source_url = _require_http_url(observation.get("source_url"), "observation.source_url")
        source_url_key = _require_http_url(observation.get("source_url_key"), "observation.source_url_key")
        observed_at = _require_iso_datetime(observation.get("observed_at"), "observation.observed_at")
        source_page_url = _optional_text(observation.get("source_page_url"), "observation.source_page_url")
        if source_page_url is not None:
            source_page_url = _require_http_url(source_page_url, "observation.source_page_url")

        source_page_artifact = None
        if observation.get("source_page_artifact_path") is not None:
            source_page_path = _safe_relative_path(
                observation.get("source_page_artifact_path"), "observation.source_page_artifact_path"
            )
            source_page_file = _resolve_file(root, source_page_path, "observation.source_page_artifact_path")
            source_page_artifact = {
                "storage_locator": source_page_path,
                "content_sha256": _sha256_file(source_page_file),
            }

        http_status = observation.get("http_status")
        if http_status is not None and (not isinstance(http_status, int) or http_status < 100 or http_status > 599):
            raise SourceObservationError("observation.http_status must be an HTTP status integer when supplied")
        content_type = _optional_text(observation.get("content_type"), "observation.content_type")
        capture_strategy = _optional_text(observation.get("capture_strategy"), "observation.capture_strategy")

        observed_pdf = None
        if retrieval_status == "succeeded":
            pdf_path = _safe_relative_path(
                observation.get("observed_pdf_path"), "observation.observed_pdf_path"
            )
            pdf_file = _resolve_file(root, pdf_path, "observation.observed_pdf_path")
            observed_sha256 = _sha256_file(pdf_file)
            supplied_sha256 = _optional_sha256(
                observation.get("observed_pdf_sha256"), "observation.observed_pdf_sha256"
            )
            if supplied_sha256 is not None and supplied_sha256 != observed_sha256:
                raise SourceObservationError(
                    "observation.observed_pdf_sha256 does not match observed_pdf_path bytes"
                )
            observed_pdf = {
                "storage_locator": pdf_path,
                "content_sha256": observed_sha256,
            }
            comparison_status = (
                "byte_identical_observed"
                if observed_sha256 == registered_sha256
                else "bytes_changed_observed"
            )
        else:
            forbidden = ("observed_pdf_path", "observed_pdf_sha256")
            if any(observation.get(field) is not None for field in forbidden):
                raise SourceObservationError(
                    "failed observations must not claim an observed PDF artifact or SHA-256"
                )
            comparison_status = "observation_failed"

        if comparison_status not in _ALLOWED_COMPARISON_STATUSES:  # defensive invariant
            raise SourceObservationError("unsupported comparison status")

        # Temporal labels are recorded only as raw source signals. Currentness remains a later reviewed decision.
        signals = _mapping(spec.get("source_signals", {}), "source_signals")
        source_issued_label = _optional_text(signals.get("source_issued_label"), "source_signals.source_issued_label")
        effective_date_signal = _optional_text(signals.get("effective_date_signal"), "source_signals.effective_date_signal")
        version_signal = _optional_text(signals.get("version_signal"), "source_signals.version_signal")

        if any(key in spec for key in ("temporal_status", "current_entitlement_publication_eligibility")):
            raise SourceObservationError(
                "source observation records must not declare temporal_status or current entitlement eligibility"
            )

        record = {
            "schema_version": "1.0",
            "record_type": "source_observation_record_v1",
            "record_status": "source_observation_recorded_review_required",
            "observation_id": observation_id,
            "registered_document": {
                "document_id": document_id,
                "document_version_id": document_version_id,
                "content_sha256": registered_sha256,
                "registration_path": registration_path,
                "registration_sha256": _sha256_file(_resolve_file(root, registration_path, "registered_document.registration_path")),
            },
            "official_observation": {
                "retrieval_status": retrieval_status,
                "source_url": source_url,
                "source_url_key": source_url_key,
                "source_page_url": source_page_url,
                "source_page_artifact": source_page_artifact,
                "observed_at": observed_at,
                "capture_strategy": capture_strategy,
                "http_status": http_status,
                "content_type": content_type,
                "observed_pdf": observed_pdf,
            },
            "byte_comparison": {
                "status": comparison_status,
                "registered_document_sha256": registered_sha256,
                "observed_document_sha256": observed_pdf["content_sha256"] if observed_pdf else None,
            },
            "source_signals": {
                "source_issued_label": source_issued_label,
                "effective_date_signal": effective_date_signal,
                "version_signal": version_signal,
            },
            "review_state": {
                "temporal_review_required": True,
                "reviewed_by_human": False,
                "review_rationale": None,
            },
            "guardrails": [
                "This record binds a timestamped official-source observation to an already-registered immutable document version.",
                "A byte-identical official observation proves only that the observed URL served the same bytes at the recorded time.",
                "This record does not itself determine document currentness, document-version compatibility, current entitlement eligibility, or insurance facts.",
                "Source-issued labels and effective-date signals are preserved as raw review inputs and require later human temporal review.",
                "Failed retrieval is recorded honestly and does not prove withdrawal, replacement, or historical status.",
            ],
            "recorded_at": recorded_at or datetime.now(timezone.utc).isoformat(),
        }
        return SourceObservationResult(record=record)

    def write_output(
        self,
        result: SourceObservationResult,
        *,
        repository_root: str | Path,
        output_path: str | Path,
    ) -> Path:
        root = Path(repository_root).resolve()
        relative = _safe_relative_path(str(output_path), "output_path")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise SourceObservationError("output_path must remain under repository_root") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result.record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target
