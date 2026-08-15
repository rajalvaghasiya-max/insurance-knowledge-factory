"""Parse a governed registered PDF directly from immutable registration metadata.

This bridge exists for Phase-2 data-only onboarding where source authority is
already represented by a governed source-registration artifact. It validates the
registered archive path and content SHA-256 before producing the same generic
parsed-PDF shape consumed by Health extraction primitives.

It does not resolve identity/currentness, adjudicate review, create facts, or
publish knowledge.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import fitz  # PyMuPDF


class GovernedRegisteredPdfParserError(ValueError):
    """Raised when a governed registration cannot be safely parsed."""


class GovernedRegisteredPdfParser:
    VERSION = "1.0"

    def __init__(self, *, repository_root: Path) -> None:
        self.root = repository_root.resolve()

    def parse(
        self,
        *,
        registration_path: str,
        source_url: str,
        entity_id: str,
        insurer_id: str,
        output_path: str | None = None,
    ) -> dict[str, Any]:
        registration_file = self._within_root(registration_path)
        registration = self._load_json(registration_file)
        document = registration.get("document")
        if not isinstance(document, Mapping):
            raise GovernedRegisteredPdfParserError("registration.document must be an object")

        sha256 = self._require_sha256(document.get("content_sha256"))
        storage_locator = self._require_nonempty(document.get("storage_locator"), "document.storage_locator")
        document_type = self._require_nonempty(document.get("document_type"), "document.document_type")
        document_id = self._require_nonempty(document.get("document_id"), "document.document_id")
        if not isinstance(source_url, str) or not source_url.strip():
            raise GovernedRegisteredPdfParserError("source_url must be non-empty")
        if not isinstance(entity_id, str) or ":" not in entity_id:
            raise GovernedRegisteredPdfParserError("entity_id must be a governed insurer:product identifier")
        if not isinstance(insurer_id, str) or not insurer_id.strip():
            raise GovernedRegisteredPdfParserError("insurer_id must be non-empty")

        pdf_path = self._within_root(storage_locator)
        archive_root = (self.root / "archive").resolve()
        try:
            pdf_path.relative_to(archive_root)
        except ValueError as exc:
            raise GovernedRegisteredPdfParserError("registered PDF must remain under archive/") from exc
        if not pdf_path.is_file():
            raise GovernedRegisteredPdfParserError(f"registered PDF not found: {storage_locator}")
        actual_sha = self._sha256_file(pdf_path)
        if actual_sha != sha256:
            raise GovernedRegisteredPdfParserError(
                f"registered PDF SHA-256 mismatch: expected {sha256}, got {actual_sha}"
            )

        pages: list[dict[str, Any]] = []
        with fitz.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                text = (page.get_text("text") or "").strip()
                pages.append({"page_number": page_number, "text": text, "char_count": len(text)})

        payload = {
            "schema_version": "1.0",
            "parser_version": self.VERSION,
            "parse_contract": "governed_registered_pdf_parse_v1",
            "parsed_at": datetime.now(timezone.utc).isoformat(),
            "entity_id": entity_id,
            "insurer_id": insurer_id,
            "document_type": document_type,
            "source_document_id": f"sha256:{sha256}",
            "registered_document_id": document_id,
            "sha256": sha256,
            "source_url": source_url.strip(),
            "source_page_url": None,
            "relative_archive_path": storage_locator,
            "provenance_status": "governed_source_registration_sha256_verified",
            "registration_path": self._relative(registration_file),
            "page_count": len(pages),
            "pages": pages,
            "guardrails": [
                "parsed evidence only",
                "no identity or currentness decision",
                "no fact selection or publication",
            ],
        }

        destination = self._within_root(output_path) if output_path else (
            self.root / "processed" / "pdf_parse" / f"{sha256}.json"
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return {
            "status": "parsed",
            "source_sha256": sha256,
            "page_count": len(pages),
            "text_page_count": sum(1 for page in pages if page["text"]),
            "output_path": self._relative(destination),
            "payload": payload,
        }

    def _within_root(self, relative_path: str | None) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise GovernedRegisteredPdfParserError("repository-relative path must be non-empty")
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise GovernedRegisteredPdfParserError("path must remain within repository root") from exc
        return candidate

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise GovernedRegisteredPdfParserError(f"registration file not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise GovernedRegisteredPdfParserError(f"invalid registration JSON: {path}") from exc
        if not isinstance(payload, dict):
            raise GovernedRegisteredPdfParserError("registration JSON root must be an object")
        return payload

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _require_sha256(value: Any) -> str:
        if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise GovernedRegisteredPdfParserError("document.content_sha256 must be lowercase SHA-256")
        return value

    @staticmethod
    def _require_nonempty(value: Any, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise GovernedRegisteredPdfParserError(f"{label} must be non-empty")
        return value.strip()

    def _relative(self, path: Path) -> str:
        return str(path.relative_to(self.root)).replace("\\", "/")
