"""P1.8 — immutable document-currentness evidence contract.

This contract records evidence bound to one registered document version and one
official source observation. It never decides temporal status, publishes facts,
or makes an entitlement conclusion. The document identity overlay remains the
only temporal decision-maker.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse


class DocumentCurrentnessEvidenceError(ValueError):
    """Raised when currentness evidence is incomplete, unsafe, or inconsistent."""


_RECORD_TYPE = "document_currentness_evidence_record_v1"
_RECORD_STATUS = "currentness_evidence_recorded_not_decided"
_OBSERVATION_TYPE = "source_observation_record_v1"
_OBSERVATION_STATUS = "source_observation_recorded_review_required"
_ALLOWED_EVIDENCE_TYPES = frozenset({
    "official_product_page_document_link",
    "official_current_policy_wording_reference",
    "official_effective_date",
    "official_version_label",
    "official_uin_reference",
    "official_replacement_reference",
    "official_withdrawal_or_archive_reference",
})
_ALLOWED_EVIDENCE_STATUSES = frozenset({
    "supports_currentness_review",
    "contradicts_currentness_review",
    "insufficient_for_currentness_review",
})
_ALLOWED_VERIFICATIONS = frozenset({
    "retained_official_html_manual_review",
    "document_embedded_text_manual_review",
    "official_page_metadata_manual_review",
})
_POSITIVE_CURRENTNESS_TYPES = frozenset({
    "official_product_page_document_link",
    "official_current_policy_wording_reference",
    "official_effective_date",
    "official_version_label",
})


@dataclass(frozen=True)
class DocumentCurrentnessEvidenceResult:
    record: Mapping[str, Any]


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise DocumentCurrentnessEvidenceError(f"{label} must be a JSON object")
    return value


def _list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise DocumentCurrentnessEvidenceError(f"{label} must be a JSON array")
    return value


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DocumentCurrentnessEvidenceError(f"{label} must be a non-empty string")
    return value.strip()


def _safe_relative_path(value: object, label: str) -> str:
    raw = _nonempty(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise DocumentCurrentnessEvidenceError(f"{label} must be a safe repository-relative path")
    return path.as_posix()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(root: Path, relative_path: str, label: str) -> Mapping[str, Any]:
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise DocumentCurrentnessEvidenceError(f"{label} must remain under repository_root") from exc
    if not path.is_file():
        raise DocumentCurrentnessEvidenceError(f"{label} was not found: {relative_path}")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DocumentCurrentnessEvidenceError(f"{label} is not valid JSON: {relative_path}") from exc
    return _mapping(parsed, label)


def _require_iso_datetime(value: object, label: str) -> str:
    raw = _nonempty(value, label)
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DocumentCurrentnessEvidenceError(f"{label} must be ISO-8601") from exc
    return raw


def _require_http_url(value: object, label: str) -> str:
    raw = _nonempty(value, label)
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise DocumentCurrentnessEvidenceError(f"{label} must be an absolute http(s) URL")
    return raw


def _require_sha256(value: object, label: str) -> str:
    raw = _nonempty(value, label).lower()
    if len(raw) != 64 or any(character not in "0123456789abcdef" for character in raw):
        raise DocumentCurrentnessEvidenceError(f"{label} must be a SHA-256 hex digest")
    return raw


def _id(*parts: str) -> str:
    raw = "|".join(parts)
    return "dce_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class DocumentCurrentnessEvidenceRecord:
    """Builds evidence-only currentness records bound to immutable artifacts."""

    RECORD_TYPE = _RECORD_TYPE
    RECORD_STATUS = _RECORD_STATUS

    def build_from_spec_file(
        self,
        *,
        spec_path: str | Path,
        repository_root: str | Path,
    ) -> DocumentCurrentnessEvidenceResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Currentness evidence specification was not found: {path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DocumentCurrentnessEvidenceError(
                f"Invalid currentness evidence specification JSON: {path}"
            ) from exc
        return self.build(spec=_mapping(raw, "currentness_evidence_spec"), repository_root=repository_root)

    def build(
        self,
        *,
        spec: Mapping[str, Any],
        repository_root: str | Path,
        recorded_at: str | None = None,
    ) -> DocumentCurrentnessEvidenceResult:
        root = Path(repository_root).resolve()
        spec = _mapping(spec, "currentness_evidence_spec")
        if spec.get("schema_version") != "1.0":
            raise DocumentCurrentnessEvidenceError("currentness_evidence_spec.schema_version must be 1.0")
        if spec.get("record_type") != _RECORD_TYPE:
            raise DocumentCurrentnessEvidenceError(
                "currentness_evidence_spec.record_type must be document_currentness_evidence_record_v1"
            )
        if spec.get("reviewed_by_human") is not True:
            raise DocumentCurrentnessEvidenceError("currentness_evidence_spec.reviewed_by_human must be true")

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
        document_sha256 = _require_sha256(
            document.get("content_sha256"), "registered_document.content_sha256"
        )

        observation_path = _safe_relative_path(
            _mapping(spec.get("source_observation"), "source_observation").get("observation_record_path"),
            "source_observation.observation_record_path",
        )
        observation = _load_json(root, observation_path, "source_observation record")
        if observation.get("record_type") != _OBSERVATION_TYPE:
            raise DocumentCurrentnessEvidenceError(
                "source observation must be source_observation_record_v1"
            )
        if observation.get("record_status") != _OBSERVATION_STATUS:
            raise DocumentCurrentnessEvidenceError(
                "source observation must be source_observation_recorded_review_required"
            )
        registered = _mapping(observation.get("registered_document"), "source observation.registered_document")
        expected = {
            "document_id": document_id,
            "document_version_id": document_version_id,
            "content_sha256": document_sha256,
            "registration_path": registration_path,
        }
        for field, value in expected.items():
            if registered.get(field) != value:
                raise DocumentCurrentnessEvidenceError(
                    f"source observation registered_document.{field} must match registered document"
                )
        comparison = _mapping(observation.get("byte_comparison"), "source observation.byte_comparison")
        if comparison.get("status") != "byte_identical_observed":
            raise DocumentCurrentnessEvidenceError(
                "currentness evidence requires byte_identical_observed source observation"
            )
        official = _mapping(observation.get("official_observation"), "source observation.official_observation")
        source_url = _require_http_url(official.get("source_url"), "source observation.official_observation.source_url")
        source_page_url = _require_http_url(
            official.get("source_page_url"),
            "source observation.official_observation.source_page_url",
        )
        source_page_artifact = _mapping(
            official.get("source_page_artifact"),
            "source observation.official_observation.source_page_artifact",
        )
        source_page_path = _safe_relative_path(
            source_page_artifact.get("storage_locator"),
            "source observation.official_observation.source_page_artifact.storage_locator",
        )
        source_page_sha = _require_sha256(
            source_page_artifact.get("content_sha256"),
            "source observation.official_observation.source_page_artifact.content_sha256",
        )
        page_file = (root / source_page_path).resolve()
        try:
            page_file.relative_to(root)
        except ValueError as exc:
            raise DocumentCurrentnessEvidenceError(
                "source page artifact must remain under repository_root"
            ) from exc
        if not page_file.is_file():
            raise DocumentCurrentnessEvidenceError("source page artifact was not found")
        if _sha256_file(page_file) != source_page_sha:
            raise DocumentCurrentnessEvidenceError("source page artifact SHA-256 does not match observation")

        items = _list(spec.get("evidence_items"), "currentness_evidence_spec.evidence_items")
        if not items:
            raise DocumentCurrentnessEvidenceError("currentness_evidence_spec.evidence_items must not be empty")
        normalized_items: list[dict[str, str]] = []
        positive_count = 0
        seen: set[tuple[str, str]] = set()
        for index, raw in enumerate(items):
            item = _mapping(raw, f"evidence_items[{index}]")
            evidence_type = _nonempty(item.get("evidence_type"), f"evidence_items[{index}].evidence_type")
            if evidence_type not in _ALLOWED_EVIDENCE_TYPES:
                raise DocumentCurrentnessEvidenceError(f"unsupported evidence_type {evidence_type!r}")
            evidence_status = _nonempty(item.get("evidence_status"), f"evidence_items[{index}].evidence_status")
            if evidence_status not in _ALLOWED_EVIDENCE_STATUSES:
                raise DocumentCurrentnessEvidenceError(f"unsupported evidence_status {evidence_status!r}")
            verification = _nonempty(item.get("verification"), f"evidence_items[{index}].verification")
            if verification not in _ALLOWED_VERIFICATIONS:
                raise DocumentCurrentnessEvidenceError(f"unsupported verification {verification!r}")
            observed_text = _nonempty(item.get("observed_text"), f"evidence_items[{index}].observed_text")
            evidence_reference = _nonempty(
                item.get("evidence_reference"), f"evidence_items[{index}].evidence_reference"
            )
            key = (evidence_type, observed_text)
            if key in seen:
                raise DocumentCurrentnessEvidenceError("evidence_items must not repeat type/observed_text pairs")
            seen.add(key)

            output = {
                "evidence_type": evidence_type,
                "evidence_status": evidence_status,
                "verification": verification,
                "observed_text": observed_text,
                "evidence_reference": evidence_reference,
            }
            if evidence_type == "official_product_page_document_link":
                linked_url = _require_http_url(
                    item.get("linked_document_url"),
                    f"evidence_items[{index}].linked_document_url",
                )
                link_label = _nonempty(item.get("link_label"), f"evidence_items[{index}].link_label")
                if linked_url != source_url:
                    raise DocumentCurrentnessEvidenceError(
                        "official_product_page_document_link must reference the observed document source_url"
                    )
                if "policy wording" not in link_label.lower():
                    raise DocumentCurrentnessEvidenceError(
                        "official_product_page_document_link link_label must identify policy wording"
                    )
                if verification != "retained_official_html_manual_review":
                    raise DocumentCurrentnessEvidenceError(
                        "official_product_page_document_link must use retained_official_html_manual_review"
                    )
                output["linked_document_url"] = linked_url
                output["link_label"] = link_label

            if evidence_status == "supports_currentness_review" and evidence_type in _POSITIVE_CURRENTNESS_TYPES:
                positive_count += 1
            normalized_items.append(output)

        reviewed_at = _require_iso_datetime(spec.get("reviewed_at"), "currentness_evidence_spec.reviewed_at")
        review_rationale = _nonempty(
            spec.get("review_rationale"), "currentness_evidence_spec.review_rationale"
        )
        record = {
            "schema_version": "1.0",
            "record_type": _RECORD_TYPE,
            "record_status": _RECORD_STATUS,
            "currentness_evidence_id": _id(document_version_id, observation.get("observation_id"), reviewed_at),
            "registered_document": {
                "document_id": document_id,
                "document_version_id": document_version_id,
                "content_sha256": document_sha256,
                "registration_path": registration_path,
                "registration_sha256": _sha256_file((root / registration_path).resolve()),
            },
            "source_observation": {
                "observation_record_path": observation_path,
                "observation_record_sha256": _sha256_file((root / observation_path).resolve()),
                "observation_id": _nonempty(observation.get("observation_id"), "source observation.observation_id"),
                "byte_comparison_status": comparison.get("status"),
                "observed_document_url": source_url,
                "source_page_url": source_page_url,
                "source_page_artifact_path": source_page_path,
                "source_page_artifact_sha256": source_page_sha,
            },
            "evidence_items": normalized_items,
            "positive_currentness_evidence_count": positive_count,
            "currentness_evidence_conclusion": (
                "sufficient_for_current_observed_review"
                if positive_count > 0
                else "insufficient_for_current_observed_review"
            ),
            "reviewed_by_human": True,
            "reviewed_at": reviewed_at,
            "review_rationale": review_rationale,
            "guardrails": [
                "This record binds currentness evidence to one registered immutable document version and one byte-identical official observation.",
                "This record is evidence only; it does not itself decide temporal status, publish facts, or determine customer entitlement.",
                "A product identity match, a functioning URL, or a reviewer rationale alone is not sufficient positive currentness evidence.",
                "Only the document identity resolution overlay may convert this evidence into a reviewed temporal status.",
            ],
            "recorded_at": recorded_at or datetime.now(timezone.utc).isoformat(),
        }
        self.validate_record(record)
        return DocumentCurrentnessEvidenceResult(record=record)

    @classmethod
    def validate_record(cls, record: Mapping[str, Any]) -> None:
        record = _mapping(record, "currentness evidence record")
        if record.get("record_type") != _RECORD_TYPE:
            raise DocumentCurrentnessEvidenceError("unsupported currentness evidence record_type")
        if record.get("record_status") != _RECORD_STATUS:
            raise DocumentCurrentnessEvidenceError("unsupported currentness evidence record_status")
        if record.get("reviewed_by_human") is not True:
            raise DocumentCurrentnessEvidenceError("currentness evidence record must be human-reviewed")
        _require_iso_datetime(record.get("reviewed_at"), "currentness evidence record.reviewed_at")
        _nonempty(record.get("review_rationale"), "currentness evidence record.review_rationale")
        _nonempty(record.get("currentness_evidence_id"), "currentness evidence record.currentness_evidence_id")
        registered = _mapping(record.get("registered_document"), "currentness evidence record.registered_document")
        for key in ("document_id", "document_version_id", "registration_path"):
            _nonempty(registered.get(key), f"currentness evidence record.registered_document.{key}")
        _require_sha256(
            registered.get("content_sha256"),
            "currentness evidence record.registered_document.content_sha256",
        )
        observation = _mapping(record.get("source_observation"), "currentness evidence record.source_observation")
        for key in (
            "observation_record_path", "observation_id", "observed_document_url",
            "source_page_url", "source_page_artifact_path",
        ):
            _nonempty(observation.get(key), f"currentness evidence record.source_observation.{key}")
        _require_sha256(
            observation.get("source_page_artifact_sha256"),
            "currentness evidence record.source_observation.source_page_artifact_sha256",
        )
        if observation.get("byte_comparison_status") != "byte_identical_observed":
            raise DocumentCurrentnessEvidenceError("currentness evidence record must bind byte_identical_observed")
        items = _list(record.get("evidence_items"), "currentness evidence record.evidence_items")
        if not items:
            raise DocumentCurrentnessEvidenceError("currentness evidence record.evidence_items must not be empty")
        positive = 0
        for index, raw in enumerate(items):
            item = _mapping(raw, f"currentness evidence record.evidence_items[{index}]")
            typ = _nonempty(item.get("evidence_type"), f"evidence_items[{index}].evidence_type")
            status = _nonempty(item.get("evidence_status"), f"evidence_items[{index}].evidence_status")
            if typ not in _ALLOWED_EVIDENCE_TYPES or status not in _ALLOWED_EVIDENCE_STATUSES:
                raise DocumentCurrentnessEvidenceError("currentness evidence record contains unsupported evidence item")
            if status == "supports_currentness_review" and typ in _POSITIVE_CURRENTNESS_TYPES:
                positive += 1
        if record.get("positive_currentness_evidence_count") != positive:
            raise DocumentCurrentnessEvidenceError("positive_currentness_evidence_count mismatch")
        expected = "sufficient_for_current_observed_review" if positive > 0 else "insufficient_for_current_observed_review"
        if record.get("currentness_evidence_conclusion") != expected:
            raise DocumentCurrentnessEvidenceError("currentness_evidence_conclusion mismatch")

    @classmethod
    def load_and_validate_for_overlay(
        cls,
        *,
        repository_root: str | Path,
        evidence_path: str,
        registration_path: str,
        document: Mapping[str, Any],
        observation_review: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        root = Path(repository_root).resolve()
        path = _safe_relative_path(evidence_path, "currentness_evidence_path")
        record = _load_json(root, path, "currentness evidence record")
        cls.validate_record(record)
        registered = _mapping(record["registered_document"], "currentness evidence record.registered_document")
        expected = {
            "document_id": document.get("document_id"),
            "document_version_id": document.get("document_version_id"),
            "content_sha256": document.get("content_sha256"),
            "registration_path": registration_path,
        }
        for key, value in expected.items():
            if registered.get(key) != value:
                raise DocumentCurrentnessEvidenceError(
                    f"currentness evidence registered_document.{key} must match overlay document"
                )
        if observation_review is None:
            raise DocumentCurrentnessEvidenceError(
                "current_observed_reviewed requires source_observation_review"
            )
        observation = _mapping(record["source_observation"], "currentness evidence record.source_observation")
        if observation.get("observation_record_path") != observation_review.get("observation_record_path"):
            raise DocumentCurrentnessEvidenceError(
                "currentness evidence must bind the same source observation reviewed by overlay"
            )
        if record.get("currentness_evidence_conclusion") != "sufficient_for_current_observed_review":
            raise DocumentCurrentnessEvidenceError(
                "current_observed_reviewed requires positive official currentness evidence"
            )
        return {
            "currentness_evidence_path": path,
            "currentness_evidence_sha256": _sha256_file((root / path).resolve()),
            "currentness_evidence_id": record["currentness_evidence_id"],
            "currentness_evidence_conclusion": record["currentness_evidence_conclusion"],
            "positive_currentness_evidence_count": record["positive_currentness_evidence_count"],
        }

    def write_output(
        self,
        result: DocumentCurrentnessEvidenceResult,
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
            raise DocumentCurrentnessEvidenceError("output_path must remain under repository_root") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result.record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target
