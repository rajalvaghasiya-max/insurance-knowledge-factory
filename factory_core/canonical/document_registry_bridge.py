"""P2.5-D: read-only document-registry bridge for Canonical Model v1.

Builds the lineage manifest required by P2.5-C from explicitly reviewed input
references. The bridge hashes actual document bytes and exact extracted-text
character ranges. It never parses a PDF, modifies inputs, or guesses identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping


class DocumentRegistryBridgeError(ValueError):
    """Raised when a lineage manifest cannot be created truthfully."""


@dataclass(frozen=True)
class DocumentRegistryBridgeResult:
    manifest: Mapping[str, Any]
    report: Mapping[str, Any]


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise DocumentRegistryBridgeError(f"{label} must be a JSON object")
    return value


def _require_list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise DocumentRegistryBridgeError(f"{label} must be a JSON array")
    return value


def _require_nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DocumentRegistryBridgeError(f"{label} must be a non-empty string")
    return value


def _require_sha256(value: object, label: str) -> str:
    digest = _require_nonempty(value, label)
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest.lower()):
        raise DocumentRegistryBridgeError(f"{label} must be a 64-character SHA-256 hex digest")
    return digest.lower()


def _require_iso_datetime(value: object, label: str) -> str:
    rendered = _require_nonempty(value, label)
    try:
        datetime.fromisoformat(rendered.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DocumentRegistryBridgeError(f"{label} must be an ISO-8601 timestamp") from exc
    return rendered


def _range_from(value: object, label: str) -> tuple[int, int]:
    item = _require_mapping(value, label)
    start, end = item.get("start"), item.get("end")
    if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
        raise DocumentRegistryBridgeError(f"{label} must contain a valid start/end range")
    return start, end


def _resolve_under_root(root: Path, raw_path: object, label: str) -> Path:
    value = _require_nonempty(raw_path, label)
    candidate = Path(value)
    if candidate.is_absolute():
        raise DocumentRegistryBridgeError(f"{label} must be relative to repository_root")
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise DocumentRegistryBridgeError(f"{label} must remain under repository_root") from exc
    if not resolved.is_file():
        raise FileNotFoundError(f"Required source file was not found: {resolved}")
    return resolved


def _relative_locator(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


class DocumentRegistryBridge:
    """Transforms explicit reviewed source references into a P2.5-C manifest."""

    def build_from_spec_file(
        self,
        *,
        spec_path: str | Path,
        repository_root: str | Path,
    ) -> DocumentRegistryBridgeResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Bridge specification was not found: {path}")
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DocumentRegistryBridgeError(f"Invalid bridge specification JSON: {path}") from exc
        return self.build(spec=spec, repository_root=repository_root, source_spec_path=str(path))

    def build(
        self,
        *,
        spec: Mapping[str, Any],
        repository_root: str | Path,
        source_spec_path: str | None = None,
    ) -> DocumentRegistryBridgeResult:
        spec = _require_mapping(spec, "bridge_spec")
        if spec.get("schema_version") != "1.0":
            raise DocumentRegistryBridgeError("bridge_spec.schema_version must be 1.0")
        root = Path(repository_root)
        if not root.is_dir():
            raise FileNotFoundError(f"repository_root was not found: {root}")

        raw_documents = _require_list(spec.get("documents"), "bridge_spec.documents")
        if not raw_documents:
            raise DocumentRegistryBridgeError("bridge_spec.documents must not be empty")

        documents: list[dict[str, Any]] = []
        evidence_spans: list[dict[str, Any]] = []
        seen_document_ids: set[str] = set()
        seen_evidence_ids: set[str] = set()
        document_paths: list[str] = []
        text_paths: list[str] = []

        for raw_document in raw_documents:
            item = _require_mapping(raw_document, "bridge_spec.documents item")
            document_id = _require_nonempty(item.get("document_id"), "document.document_id")
            if document_id in seen_document_ids:
                raise DocumentRegistryBridgeError(f"Duplicate document.document_id: {document_id}")
            seen_document_ids.add(document_id)
            source_document_id = _require_nonempty(item.get("source_document_id"), "document.source_document_id")
            document_version_id = _require_nonempty(item.get("document_version_id"), "document.document_version_id")
            document_type = _require_nonempty(item.get("document_type"), "document.document_type")
            canonical_title = _require_nonempty(item.get("canonical_title"), "document.canonical_title")
            captured_at = _require_iso_datetime(item.get("captured_at"), "document.captured_at")
            document_path = _resolve_under_root(root, item.get("document_path"), "document.document_path")
            text_path = _resolve_under_root(root, item.get("extracted_text_path"), "document.extracted_text_path")
            content_sha256 = _sha256_bytes(document_path.read_bytes())
            expected_content_sha256 = item.get("expected_content_sha256")
            if expected_content_sha256 is not None and _require_sha256(expected_content_sha256, "document.expected_content_sha256") != content_sha256:
                raise DocumentRegistryBridgeError(f"Document content hash mismatch for document_id: {document_id}")

            manifest_document: dict[str, Any] = {
                "document_id": document_id,
                "source_document_id": source_document_id,
                "document_version_id": document_version_id,
                "content_sha256": content_sha256,
                "captured_at": captured_at,
                "document_type": document_type,
                "canonical_title": canonical_title,
                "storage_locator": _relative_locator(root, document_path),
            }
            for optional in ("effective_from", "effective_to", "source_url"):
                if item.get(optional) is not None:
                    manifest_document[optional] = _require_nonempty(item[optional], f"document.{optional}")
            documents.append(manifest_document)
            document_paths.append(manifest_document["storage_locator"])
            text_paths.append(_relative_locator(root, text_path))

            text = text_path.read_text(encoding="utf-8")
            raw_spans = _require_list(item.get("evidence_spans"), "document.evidence_spans")
            if not raw_spans:
                raise DocumentRegistryBridgeError(f"document.evidence_spans must not be empty for document_id: {document_id}")
            for raw_span in raw_spans:
                span = _require_mapping(raw_span, "document.evidence_spans item")
                evidence_id = _require_nonempty(span.get("evidence_id"), "evidence_span.evidence_id")
                if evidence_id in seen_evidence_ids:
                    raise DocumentRegistryBridgeError(f"Duplicate evidence_span.evidence_id: {evidence_id}")
                seen_evidence_ids.add(evidence_id)
                start, end = _range_from(span.get("source_char_range"), "evidence_span.source_char_range")
                if end > len(text):
                    raise DocumentRegistryBridgeError(
                        f"evidence_span.source_char_range exceeds extracted text length for evidence_id: {evidence_id}"
                    )
                excerpt = text[start:end]
                if not excerpt:
                    raise DocumentRegistryBridgeError(f"Evidence span is empty for evidence_id: {evidence_id}")
                text_sha256 = _sha256_bytes(excerpt.encode("utf-8"))
                expected_text_sha256 = span.get("expected_text_sha256")
                if expected_text_sha256 is not None and _require_sha256(expected_text_sha256, "evidence_span.expected_text_sha256") != text_sha256:
                    raise DocumentRegistryBridgeError(f"Evidence text hash mismatch for evidence_id: {evidence_id}")
                manifest_span: dict[str, Any] = {
                    "evidence_id": evidence_id,
                    "document_id": document_id,
                    "document_version_id": document_version_id,
                    "source_char_range": {"start": start, "end": end},
                    "text_sha256": text_sha256,
                    "extraction_method": _require_nonempty(span.get("extraction_method"), "evidence_span.extraction_method"),
                }
                source_page = span.get("source_page")
                if source_page is not None:
                    if not isinstance(source_page, int) or source_page <= 0:
                        raise DocumentRegistryBridgeError("evidence_span.source_page must be a positive integer")
                    manifest_span["source_page"] = source_page
                evidence_spans.append(manifest_span)

        manifest = {
            "schema_version": "1.0",
            "documents": sorted(documents, key=lambda row: row["document_id"]),
            "evidence_spans": sorted(evidence_spans, key=lambda row: row["evidence_id"]),
        }
        report = {
            "schema_version": "1.0",
            "bridge_type": "document_registry_bridge_v1",
            "bridge_status": "validated_read_only_lineage_manifest",
            "repository_root": str(root.resolve()),
            "source_spec_path": source_spec_path,
            "document_count": len(manifest["documents"]),
            "evidence_span_count": len(manifest["evidence_spans"]),
            "source_document_paths": document_paths,
            "source_extracted_text_paths": text_paths,
            "notes": [
                "Content hashes were computed from actual document bytes.",
                "Evidence text hashes were computed from exact extracted-text character ranges.",
                "The bridge did not parse documents, mutate inputs, publish assertions, or alter legacy artifacts.",
            ],
        }
        return DocumentRegistryBridgeResult(manifest=manifest, report=report)

    def write_manifest(
        self,
        result: DocumentRegistryBridgeResult,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "1.0",
            "report": dict(result.report),
            "lineage_manifest": dict(result.manifest),
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path
