"""Parse registry-backed Health PDFs without copying or renaming raw evidence."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from config.settings import BASE_DIR

PARSER_VERSION = "1.0"


class RegistryBackedPdfParser:
    """Create immutable, hash-addressed parse artifacts from evidence-intake records.

    The intake registry is the handoff contract. This parser does not rediscover
    PDFs, infer product ownership, or modify raw evidence. A matching parse-registry
    entry is reused on repeated runs unless ``force`` is requested.
    """

    def __init__(self, *, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or BASE_DIR

    @property
    def intake_registry_path(self) -> Path:
        return self.base_dir / "registry" / "product_evidence_intake_registry.json"

    @property
    def parse_registry_path(self) -> Path:
        return self.base_dir / "registry" / "pdf_parse_registry.json"

    @property
    def report_path(self) -> Path:
        return self.base_dir / "reports" / "registry_backed_pdf_parse_report.json"

    def build(self, *, entity_id: str, force: bool = False) -> dict[str, Any]:
        intake = self._load_json(self.intake_registry_path)
        selected = [
            item for item in intake.get("records", [])
            if isinstance(item, dict)
            and item.get("entity_id") == entity_id
            and item.get("intake_status") == "ready_for_processing"
        ]
        selected.sort(key=lambda item: (self._document_rank(item.get("document_type")), str(item.get("sha256") or "")))

        existing_registry = self._load_existing_registry()
        existing_by_key = {
            self._registry_key(item): item
            for item in existing_registry.get("records", [])
            if isinstance(item, dict)
        }

        report_records: list[dict[str, Any]] = []
        new_registry_records: list[dict[str, Any]] = []
        for item in selected:
            result = self._parse_or_reuse(item, existing_by_key, force=force)
            report_records.append(result)
            if result.get("parse_record"):
                new_registry_records.append(result["parse_record"])

        retained = [
            item for item in existing_registry.get("records", [])
            if isinstance(item, dict) and item.get("entity_id") != entity_id
        ]
        registry_records = retained + new_registry_records
        registry_records.sort(key=lambda item: (str(item.get("entity_id") or ""), self._document_rank(item.get("document_type")), str(item.get("sha256") or "")))

        registry = {
            "schema_version": "1.0",
            "parser_version": PARSER_VERSION,
            "generated_at": self._utc_now(),
            "records": registry_records,
        }
        counts = Counter(result["status"] for result in report_records)
        report = {
            "schema_version": "1.0",
            "parser_version": PARSER_VERSION,
            "generated_at": self._utc_now(),
            "entity_id": entity_id,
            "intake_records_selected": len(selected),
            "status_counts": {
                "parsed": counts.get("parsed", 0),
                "reused": counts.get("reused", 0),
                "blocked_integrity_mismatch": counts.get("blocked_integrity_mismatch", 0),
                "blocked_missing_archive_file": counts.get("blocked_missing_archive_file", 0),
                "failed": counts.get("failed", 0),
            },
            "records": [{key: value for key, value in item.items() if key != "parse_record"} for item in report_records],
            "notes": [
                "Raw PDFs are read in place and never copied, renamed, or modified.",
                "Each parsed artifact is hash-addressed and retains immutable source provenance.",
                "The parser consumes the evidence-intake registry and does not rediscover source documents.",
            ],
        }
        self._write_json(self.parse_registry_path, registry)
        self._write_json(self.report_path, report)
        return {"report": report, "registry_path": self.parse_registry_path, "report_path": self.report_path}

    def _parse_or_reuse(self, intake_record: dict[str, Any], existing_by_key: dict[str, dict[str, Any]], *, force: bool) -> dict[str, Any]:
        sha256 = str(intake_record.get("sha256") or "")
        document_type = str(intake_record.get("document_type") or "unknown")
        archive_path = self._resolve_archive_path(intake_record.get("relative_archive_path"))
        base_result = {
            "entity_id": intake_record.get("entity_id"),
            "document_type": document_type,
            "source_document_id": intake_record.get("source_document_id"),
            "sha256": sha256,
            "relative_archive_path": intake_record.get("relative_archive_path"),
        }
        if archive_path is None or not archive_path.is_file():
            return {**base_result, "status": "blocked_missing_archive_file"}
        actual_hash = self._sha256_file(archive_path)
        if actual_hash != sha256:
            return {**base_result, "status": "blocked_integrity_mismatch", "actual_sha256": actual_hash}

        key = self._registry_key(intake_record)
        existing = existing_by_key.get(key)
        if not force and self._is_reusable(existing):
            return {
                **base_result,
                "status": "reused",
                "output_path": existing.get("output_path"),
                "page_count": existing.get("page_count"),
                "parse_record": existing,
            }

        try:
            payload = self._parse_pdf(intake_record, archive_path)
            output_path = self._output_path(sha256)
            self._write_json(output_path, payload)
            parse_record = {
                "parse_id": self._stable_id("pp", f"{intake_record.get('entity_id')}|{sha256}|{PARSER_VERSION}"),
                "entity_id": intake_record.get("entity_id"),
                "insurer_id": intake_record.get("insurer_id"),
                "product_name": intake_record.get("product_name"),
                "document_type": document_type,
                "source_document_id": intake_record.get("source_document_id"),
                "sha256": sha256,
                "relative_archive_path": intake_record.get("relative_archive_path"),
                "source_url": intake_record.get("source_url"),
                "source_page_url": intake_record.get("source_page_url"),
                "provenance_status": intake_record.get("provenance_status"),
                "parser_version": PARSER_VERSION,
                "page_count": payload["page_count"],
                "output_path": self._relative_path(output_path),
                "parsed_at": payload["parsed_at"],
                "parse_status": "parsed",
            }
            return {**base_result, "status": "parsed", "output_path": parse_record["output_path"], "page_count": payload["page_count"], "parse_record": parse_record}
        except (fitz.FileDataError, RuntimeError, OSError, ValueError) as exc:
            return {**base_result, "status": "failed", "error": str(exc)}

    def _parse_pdf(self, intake_record: dict[str, Any], archive_path: Path) -> dict[str, Any]:
        pages: list[dict[str, Any]] = []
        with fitz.open(archive_path) as document:
            for page_number, page in enumerate(document, start=1):
                text = (page.get_text("text") or "").strip()
                pages.append({"page_number": page_number, "text": text, "char_count": len(text)})
        return {
            "schema_version": "1.0",
            "parser_version": PARSER_VERSION,
            "parsed_at": self._utc_now(),
            "entity_id": intake_record.get("entity_id"),
            "insurer_id": intake_record.get("insurer_id"),
            "product_name": intake_record.get("product_name"),
            "document_type": intake_record.get("document_type"),
            "source_document_id": intake_record.get("source_document_id"),
            "sha256": intake_record.get("sha256"),
            "source_url": intake_record.get("source_url"),
            "source_page_url": intake_record.get("source_page_url"),
            "relative_archive_path": intake_record.get("relative_archive_path"),
            "provenance_status": intake_record.get("provenance_status"),
            "page_count": len(pages),
            "pages": pages,
        }

    def _is_reusable(self, record: dict[str, Any] | None) -> bool:
        if not record or record.get("parse_status") != "parsed" or record.get("parser_version") != PARSER_VERSION:
            return False
        output_path = record.get("output_path")
        return isinstance(output_path, str) and (self.base_dir / output_path).is_file()

    def _output_path(self, sha256: str) -> Path:
        return self.base_dir / "processed" / "pdf_parse" / f"{sha256}.json"

    def _resolve_archive_path(self, relative_path: Any) -> Path | None:
        if not isinstance(relative_path, str) or not relative_path.startswith("archive/"):
            return None
        candidate = (self.base_dir / relative_path).resolve()
        archive_root = (self.base_dir / "archive").resolve()
        try:
            candidate.relative_to(archive_root)
        except ValueError:
            return None
        return candidate

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _registry_key(item: dict[str, Any]) -> str:
        return "|".join((str(item.get("entity_id") or ""), str(item.get("sha256") or ""), PARSER_VERSION))

    @staticmethod
    def _document_rank(document_type: Any) -> int:
        return {"policy_wording": 1, "customer_information_sheet": 2, "prospectus": 3, "brochure": 4, "proposal_form": 5}.get(str(document_type), 99)

    def _load_existing_registry(self) -> dict[str, Any]:
        if not self.parse_registry_path.exists():
            return {"records": []}
        return self._load_json(self.parse_registry_path)

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Required JSON file not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON file: {path}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"JSON root must be an object: {path}")
        return payload

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _relative_path(self, path: Path) -> str:
        return str(path.relative_to(self.base_dir)).replace("\\", "/")

    @staticmethod
    def _stable_id(prefix: str, value: str) -> str:
        return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
