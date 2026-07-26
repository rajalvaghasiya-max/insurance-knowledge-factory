"""Audit registry-backed PDF parse artifacts before fact extraction."""
from __future__ import annotations

import json
import statistics
from math import ceil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR

AUDIT_VERSION = "1.0"
MIN_TOTAL_CHARACTERS = 500
MIN_NONEMPTY_PAGE_RATIO = 0.80
MIN_MEDIAN_CHARS_PER_PAGE = 80
SHORT_PAGE_CHARACTER_THRESHOLD = 250


class PdfParseQualityAudit:
    """Evaluate known parse artifacts from the PDF Parse Registry.

    This audit consumes parse-registry records. It never searches archive folders,
    opens raw PDFs, or changes parse outputs. It classifies whether a parse artifact
    is safe to send to downstream extraction, needs human review, or is blocked.
    """

    def __init__(self, *, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or BASE_DIR

    @property
    def parse_registry_path(self) -> Path:
        return self.base_dir / "registry" / "pdf_parse_registry.json"

    @property
    def quality_registry_path(self) -> Path:
        return self.base_dir / "registry" / "pdf_parse_quality_registry.json"

    @property
    def report_path(self) -> Path:
        return self.base_dir / "reports" / "pdf_parse_quality_report.json"

    def build(self, *, entity_id: str) -> dict[str, Any]:
        parse_registry = self._load_json(self.parse_registry_path)
        selected = [
            item for item in parse_registry.get("records", [])
            if isinstance(item, dict)
            and item.get("entity_id") == entity_id
            and item.get("parse_status") == "parsed"
        ]
        selected.sort(key=lambda item: (self._document_rank(item.get("document_type")), str(item.get("sha256") or "")))

        audit_records = [self._audit_record(item) for item in selected]
        retained = [
            item for item in self._load_existing_quality_registry().get("records", [])
            if isinstance(item, dict) and item.get("entity_id") != entity_id
        ]
        records = retained + audit_records
        records.sort(key=lambda item: (str(item.get("entity_id") or ""), self._document_rank(item.get("document_type")), str(item.get("sha256") or "")))

        counts = Counter(record["quality_status"] for record in audit_records)
        registry = {
            "schema_version": "1.0",
            "audit_version": AUDIT_VERSION,
            "generated_at": self._utc_now(),
            "records": records,
        }
        report = {
            "schema_version": "1.0",
            "audit_version": AUDIT_VERSION,
            "generated_at": self._utc_now(),
            "entity_id": entity_id,
            "parse_records_selected": len(selected),
            "status_counts": {
                "ready_for_extraction": counts.get("ready_for_extraction", 0),
                "needs_review": counts.get("needs_review", 0),
                "blocked": counts.get("blocked", 0),
            },
            "records": audit_records,
            "notes": [
                "The audit consumes PDF Parse Registry records and does not rediscover source documents.",
                "Raw PDFs and parse artifacts are never modified by this audit.",
                "A ready result confirms basic structural text quality only; it is not a claim that extracted facts are correct.",
            ],
        }
        self._write_json(self.quality_registry_path, registry)
        self._write_json(self.report_path, report)
        return {"report": report, "registry_path": self.quality_registry_path, "report_path": self.report_path}

    def _audit_record(self, parse_record: dict[str, Any]) -> dict[str, Any]:
        base = {
            "quality_audit_id": self._stable_id("pqa", f"{parse_record.get('entity_id')}|{parse_record.get('sha256')}|{AUDIT_VERSION}"),
            "entity_id": parse_record.get("entity_id"),
            "insurer_id": parse_record.get("insurer_id"),
            "product_name": parse_record.get("product_name"),
            "document_type": parse_record.get("document_type"),
            "source_document_id": parse_record.get("source_document_id"),
            "sha256": parse_record.get("sha256"),
            "parse_id": parse_record.get("parse_id"),
            "parser_version": parse_record.get("parser_version"),
            "parse_output_path": parse_record.get("output_path"),
            "audit_version": AUDIT_VERSION,
        }
        output_path = self._resolve_processed_path(parse_record.get("output_path"))
        if output_path is None or not output_path.is_file():
            return {**base, "quality_status": "blocked", "blockers": ["missing_parse_artifact"], "warnings": [], "metrics": {}}

        try:
            artifact = self._load_json(output_path)
        except (ValueError, OSError) as exc:
            return {**base, "quality_status": "blocked", "blockers": ["invalid_parse_artifact"], "warnings": [str(exc)], "metrics": {}}

        pages = artifact.get("pages")
        declared_page_count = artifact.get("page_count")
        if not isinstance(pages, list) or not isinstance(declared_page_count, int):
            return {**base, "quality_status": "blocked", "blockers": ["missing_page_structure"], "warnings": [], "metrics": {}}
        if declared_page_count != len(pages):
            return {**base, "quality_status": "blocked", "blockers": ["page_count_mismatch"], "warnings": [], "metrics": {"declared_page_count": declared_page_count, "actual_page_count": len(pages)}}
        if declared_page_count <= 0:
            return {**base, "quality_status": "blocked", "blockers": ["zero_pages"], "warnings": [], "metrics": {"declared_page_count": declared_page_count}}

        expected_page_numbers = list(range(1, declared_page_count + 1))
        actual_page_numbers = [page.get("page_number") if isinstance(page, dict) else None for page in pages]
        if actual_page_numbers != expected_page_numbers:
            return {**base, "quality_status": "blocked", "blockers": ["non_sequential_page_numbers"], "warnings": [], "metrics": {"declared_page_count": declared_page_count}}

        char_counts = [self._page_char_count(page) for page in pages]
        nonempty_page_count = sum(count > 0 for count in char_counts)
        total_characters = sum(char_counts)
        nonempty_ratio = nonempty_page_count / declared_page_count
        median_characters = float(statistics.median(char_counts))
        short_pages = [index + 1 for index, count in enumerate(char_counts) if 0 < count < SHORT_PAGE_CHARACTER_THRESHOLD]
        blockers: list[str] = []
        warnings: list[str] = []
        if total_characters < MIN_TOTAL_CHARACTERS:
            blockers.append("insufficient_total_text")
        if nonempty_ratio < MIN_NONEMPTY_PAGE_RATIO:
            blockers.append("low_nonempty_page_ratio")
        if median_characters < MIN_MEDIAN_CHARS_PER_PAGE:
            warnings.append("low_median_text_per_page")
        short_page_review_threshold = max(2, ceil(declared_page_count * 0.20))
        if len(short_pages) >= short_page_review_threshold:
            warnings.append("short_text_pages_present")

        quality_status = "blocked" if blockers else "needs_review" if warnings else "ready_for_extraction"
        return {
            **base,
            "quality_status": quality_status,
            "blockers": blockers,
            "warnings": warnings,
            "metrics": {
                "page_count": declared_page_count,
                "total_characters": total_characters,
                "nonempty_page_count": nonempty_page_count,
                "nonempty_page_ratio": round(nonempty_ratio, 4),
                "median_characters_per_page": median_characters,
                "short_text_page_count": len(short_pages),
                "short_text_page_review_threshold": short_page_review_threshold,
                "short_text_pages": short_pages,
            },
        }

    @staticmethod
    def _page_char_count(page: Any) -> int:
        if not isinstance(page, dict):
            return 0
        char_count = page.get("char_count")
        if isinstance(char_count, int) and char_count >= 0:
            return char_count
        text = page.get("text")
        return len(text) if isinstance(text, str) else 0

    def _resolve_processed_path(self, relative_path: Any) -> Path | None:
        if not isinstance(relative_path, str) or not relative_path.startswith("processed/"):
            return None
        candidate = (self.base_dir / relative_path).resolve()
        processed_root = (self.base_dir / "processed").resolve()
        try:
            candidate.relative_to(processed_root)
        except ValueError:
            return None
        return candidate

    def _load_existing_quality_registry(self) -> dict[str, Any]:
        if not self.quality_registry_path.exists():
            return {"records": []}
        return self._load_json(self.quality_registry_path)

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

    @staticmethod
    def _document_rank(document_type: Any) -> int:
        return {"policy_wording": 1, "customer_information_sheet": 2, "prospectus": 3, "brochure": 4, "proposal_form": 5}.get(str(document_type), 99)

    @staticmethod
    def _stable_id(prefix: str, value: str) -> str:
        import hashlib
        return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
