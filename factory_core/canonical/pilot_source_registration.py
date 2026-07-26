"""P2.5-F2 — controlled source registration for a canonical pilot.

Registers one explicitly supplied source PDF, creates deterministic extracted
text, and emits *review candidates* for evidence spans.  It never infers a
source identity from file names, publishes rules, edits registries, or binds a
candidate span to a legacy evidence id without human review.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence


class PilotSourceRegistrationError(ValueError):
    """Raised when pilot source registration cannot be performed truthfully."""


@dataclass(frozen=True)
class PilotSourceRegistrationResult:
    registration: Mapping[str, Any]
    extracted_text: str


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise PilotSourceRegistrationError(f"{label} must be a JSON object")
    return value


def _require_list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise PilotSourceRegistrationError(f"{label} must be a JSON array")
    return value


def _require_nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PilotSourceRegistrationError(f"{label} must be a non-empty string")
    return value.strip()


def _resolve_under_root(root: Path, raw_path: object, label: str, *, must_exist: bool = True) -> Path:
    relative = Path(_require_nonempty(raw_path, label))
    if relative.is_absolute() or re.match(r"^[A-Za-z]:[\\/]", str(relative)):
        raise PilotSourceRegistrationError(f"{label} must be relative to repository_root")
    root = root.resolve()
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PilotSourceRegistrationError(f"{label} must remain under repository_root") from exc
    if must_exist and not resolved.is_file():
        raise FileNotFoundError(f"Required source file was not found: {resolved}")
    return resolved


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _safe_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")


def _version_id(document_id: str, content_sha256: str) -> str:
    return f"docver_{_safe_identifier(document_id)}_{content_sha256[:16]}"


def _normalize_for_marker(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _page_texts_from_pdf(path: Path) -> list[str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - depends on caller environment
        raise PilotSourceRegistrationError(
            "P2.5-F2 requires pypdf for deterministic text extraction. Install it in the project virtual environment."
        ) from exc
    try:
        reader = PdfReader(str(path))
        return [(page.extract_text() or "") for page in reader.pages]
    except Exception as exc:  # pypdf error types vary by version
        raise PilotSourceRegistrationError(f"Unable to extract text from PDF: {path}") from exc


class PilotSourceRegistration:
    """Registers an explicit PDF and creates evidence-review candidates only."""

    def register_from_spec_file(self, *, spec_path: str | Path, repository_root: str | Path) -> PilotSourceRegistrationResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Registration specification was not found: {path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PilotSourceRegistrationError(f"Invalid registration specification JSON: {path}") from exc
        return self.register(spec=raw, repository_root=repository_root)

    def register(
        self,
        *,
        spec: Mapping[str, Any],
        repository_root: str | Path,
        page_text_extractor: Callable[[Path], Sequence[str]] | None = None,
        registered_at: str | None = None,
    ) -> PilotSourceRegistrationResult:
        spec = _require_mapping(spec, "registration_spec")
        if spec.get("schema_version") != "1.0":
            raise PilotSourceRegistrationError("registration_spec.schema_version must be 1.0")
        if spec.get("registration_type") != "pilot_source_registration_v1":
            raise PilotSourceRegistrationError("registration_spec.registration_type must be pilot_source_registration_v1")
        root = Path(repository_root)
        if not root.is_dir():
            raise FileNotFoundError(f"repository_root was not found: {root}")

        document_id = _require_nonempty(spec.get("document_id"), "registration_spec.document_id")
        source_document_id = _require_nonempty(spec.get("source_document_id"), "registration_spec.source_document_id")
        canonical_title = _require_nonempty(spec.get("canonical_title"), "registration_spec.canonical_title")
        document_type = _require_nonempty(spec.get("document_type"), "registration_spec.document_type")
        document_path = _resolve_under_root(root, spec.get("document_path"), "registration_spec.document_path")
        if document_path.suffix.casefold() != ".pdf":
            raise PilotSourceRegistrationError("registration_spec.document_path must point to a PDF")

        markers = [_require_nonempty(item, "registration_spec.evidence_markers item") for item in _require_list(spec.get("evidence_markers"), "registration_spec.evidence_markers")]
        if not markers:
            raise PilotSourceRegistrationError("registration_spec.evidence_markers must not be empty")

        document_bytes = document_path.read_bytes()
        document_sha256 = _sha256_bytes(document_bytes)
        extractor = page_text_extractor or _page_texts_from_pdf
        page_texts = list(extractor(document_path))
        if not page_texts:
            raise PilotSourceRegistrationError("PDF extraction produced no pages")

        page_offsets: list[int] = []
        chunks: list[str] = []
        offset = 0
        for index, page_text in enumerate(page_texts, start=1):
            if not isinstance(page_text, str):
                raise PilotSourceRegistrationError("PDF extraction must return text strings")
            page_offsets.append(offset)
            chunk = f"\n\n===== PAGE {index} =====\n{page_text.rstrip()}\n"
            chunks.append(chunk)
            offset += len(chunk)
        extracted_text = "".join(chunks)
        extracted_text_sha256 = _sha256_bytes(extracted_text.encode("utf-8"))

        candidates = self._find_candidates(extracted_text, page_texts, page_offsets, markers)
        registration = {
            "schema_version": "1.0",
            "registration_type": "pilot_source_registration_v1",
            "registration_status": "source_registered_evidence_review_required",
            "document": {
                "document_id": document_id,
                "source_document_id": source_document_id,
                "document_version_id": _version_id(document_id, document_sha256),
                "canonical_title": canonical_title,
                "document_type": document_type,
                "content_sha256": document_sha256,
                "storage_locator": _relative(root, document_path),
                "source_issued_label": spec.get("source_issued_label"),
            },
            "extracted_text": {
                "text_sha256": extracted_text_sha256,
                "page_count": len(page_texts),
                "extraction_method": "pypdf_text_v1",
                "storage_locator": _require_nonempty(spec.get("extracted_text_output_path"), "registration_spec.extracted_text_output_path"),
            },
            "evidence_review": {
                "status": "human_selection_required",
                "legacy_evidence_binding": "not_performed",
                "candidate_count": len(candidates),
                "candidates": candidates,
            },
            "registered_at": registered_at or datetime.now(timezone.utc).isoformat(),
            "notes": [
                "The PDF was supplied explicitly by the reviewer; source identity was not inferred from its filename.",
                "Candidate spans are discovery aids only and are not bound to legacy evidence IDs.",
                "This record does not modify registry files, triage artifacts, publication receipts, conditional rules, or authority state.",
            ],
        }
        return PilotSourceRegistrationResult(registration=registration, extracted_text=extracted_text)

    @staticmethod
    def _find_candidates(
        extracted_text: str,
        page_texts: Sequence[str],
        page_offsets: Sequence[int],
        markers: Sequence[str],
    ) -> list[dict[str, Any]]:
        normalized_markers = [_normalize_for_marker(marker) for marker in markers]
        results: list[dict[str, Any]] = []
        for page_no, raw_page in enumerate(page_texts, start=1):
            normalized_page = _normalize_for_marker(raw_page)
            matched = [marker for marker, normalized in zip(markers, normalized_markers) if normalized in normalized_page]
            if not matched:
                continue
            # Candidate is the exact extracted page block, never a guessed sub-range.
            marker = f"\n\n===== PAGE {page_no} =====\n"
            start = extracted_text.find(marker)
            if start < 0:
                continue
            end_marker = f"\n\n===== PAGE {page_no + 1} =====\n"
            end = extracted_text.find(end_marker, start + len(marker))
            if end < 0:
                end = len(extracted_text)
            excerpt = extracted_text[start:end]
            results.append({
                "candidate_id": f"candidate_page_{page_no}",
                "source_page": page_no,
                "source_char_range": {"start": start, "end": end},
                "text_sha256": _sha256_bytes(excerpt.encode("utf-8")),
                "matched_markers": matched,
                "excerpt": excerpt,
                "review_required": True,
            })
        return results

    def write_outputs(
        self,
        result: PilotSourceRegistrationResult,
        *,
        repository_root: str | Path,
        registration_output_path: str | Path,
        extracted_text_output_path: str | Path,
    ) -> tuple[Path, Path]:
        root = Path(repository_root)
        registration_path = _resolve_under_root(root, registration_output_path, "registration_output_path", must_exist=False)
        text_path = _resolve_under_root(root, extracted_text_output_path, "extracted_text_output_path", must_exist=False)
        registration_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.write_text(result.extracted_text, encoding="utf-8")
        registration_path.write_text(json.dumps(dict(result.registration), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return registration_path, text_path
