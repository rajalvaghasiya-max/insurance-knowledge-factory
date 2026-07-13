"""Parse selected P1.6 benchmark PDFs without creating product knowledge.

This is deliberately a benchmark-only parser. It reads immutable raw PDFs in
place, verifies their SHA-256 against the candidate inventory, and writes
hash-addressed native-text parse artifacts. It never changes source identity,
product evidence intake, facts, or publication status.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import fitz  # PyMuPDF


PARSER_VERSION = "1.0"


class PdfBenchmarkSelectionError(ValueError):
    """Raised for invalid benchmark selection inputs."""


class PdfBenchmarkSelectedParser:
    """Create benchmark-only native-text parse artifacts from selected candidates."""

    def __init__(self, *, base_dir: Path) -> None:
        self.base_dir = base_dir

    @property
    def selection_path(self) -> Path:
        return self.base_dir / "examples" / "pdf_benchmark" / "p1_6_benchmark_selection.v1.json"

    @property
    def inventory_path(self) -> Path:
        return self.base_dir / "registry" / "pdf_benchmark_candidate_inventory_v1.json"

    @property
    def parse_registry_path(self) -> Path:
        return self.base_dir / "registry" / "pdf_parse_registry.json"

    @property
    def report_path(self) -> Path:
        return self.base_dir / "reports" / "pdf_benchmark_selected_parse_report.json"

    def build(self, *, selection_path: Path | None = None, force: bool = False) -> dict[str, Any]:
        selection = self._load_object(selection_path or self.selection_path)
        inventory = self._load_object(self.inventory_path)
        self._validate_selection(selection)
        by_candidate_id = {
            str(item.get("candidate_id")): item
            for item in inventory.get("candidates", [])
            if isinstance(item, dict)
        }

        existing_registry = self._load_existing_registry()
        existing_by_id = {
            str(item.get("parse_id")): item
            for item in existing_registry.get("records", [])
            if isinstance(item, dict)
        }

        results = [self._parse_case(case, by_candidate_id, existing_by_id, force=force) for case in selection["selected_cases"]]
        retained = [
            item for item in existing_registry.get("records", [])
            if isinstance(item, dict) and str(item.get("parse_id")) not in {result["parse_id"] for result in results}
        ]
        created = [result["parse_record"] for result in results if result.get("parse_record")]
        records = retained + created
        records.sort(key=lambda item: (str(item.get("entity_id") or ""), str(item.get("document_type") or ""), str(item.get("sha256") or "")))
        self._write_object(self.parse_registry_path, {
            "schema_version": "1.0",
            "parser_version": PARSER_VERSION,
            "generated_at": self._utc_now(),
            "records": records,
        })

        counts = Counter(item["status"] for item in results)
        report = {
            "schema_version": "1.0",
            "parser_version": PARSER_VERSION,
            "selection_id": selection["selection_id"],
            "generated_at": self._utc_now(),
            "selected_case_count": len(selection["selected_cases"]),
            "status_counts": {
                "parsed": counts.get("parsed", 0),
                "reused": counts.get("reused", 0),
                "blocked": counts.get("blocked", 0),
                "failed": counts.get("failed", 0),
            },
            "records": [{key: value for key, value in result.items() if key != "parse_record"} for result in results],
            "notes": [
                "Benchmark-only parse artifacts are not product evidence intake records.",
                "No product identity, currentness, fact, or publication decision is created or changed.",
                "Raw PDFs are read in place after SHA-256 verification and are never copied, renamed, or modified.",
            ],
        }
        self._write_object(self.report_path, report)
        return {"report": report, "report_path": self.report_path, "parse_registry_path": self.parse_registry_path}

    def _parse_case(self, case: dict[str, Any], by_candidate_id: dict[str, dict[str, Any]], existing_by_id: dict[str, dict[str, Any]], *, force: bool) -> dict[str, Any]:
        candidate_id = str(case["candidate_id"])
        parse_id = self.parse_id_for(candidate_id=candidate_id, sha256=str(case["sha256"]))
        base = {"case_id": case["case_id"], "candidate_id": candidate_id, "parse_id": parse_id}
        candidate = by_candidate_id.get(candidate_id)
        if candidate is None:
            return {**base, "status": "blocked", "blockers": ["candidate_not_found"]}
        try:
            self._validate_candidate(case, candidate)
            raw_path = self._resolve_raw_path(candidate.get("raw_pdf_relative_path"))
            if raw_path is None or not raw_path.is_file():
                return {**base, "status": "blocked", "blockers": ["raw_pdf_not_found"]}
            actual = self._sha256_file(raw_path)
            if actual != candidate["sha256"]:
                return {**base, "status": "blocked", "blockers": ["raw_pdf_hash_mismatch"], "actual_sha256": actual}
            existing = existing_by_id.get(parse_id)
            if not force and self._is_reusable(existing):
                return {**base, "status": "reused", "output_path": existing["output_path"], "page_count": existing["page_count"], "parse_record": existing}
            payload = self._parse_pdf(case, candidate, raw_path)
            output = self.base_dir / "processed" / "pdf_parse" / f"{candidate['sha256']}.json"
            self._write_object(output, payload)
            record = {
                "parse_id": parse_id,
                "entity_id": None,
                "insurer_id": candidate["insurer_id"],
                "product_name": None,
                "document_type": candidate["document_type"],
                "source_document_id": f"sha256:{candidate['sha256']}",
                "sha256": candidate["sha256"],
                "relative_archive_path": candidate["raw_pdf_relative_path"],
                "source_url": candidate["source_url"],
                "source_page_url": candidate.get("source_page_url"),
                "provenance_status": "official_registry_candidate_inventory",
                "parser_version": PARSER_VERSION,
                "page_count": payload["page_count"],
                "output_path": self._relative_path(output),
                "parsed_at": payload["parsed_at"],
                "parse_status": "parsed",
                "benchmark_only": True,
                "benchmark_case_id": case["case_id"],
                "benchmark_candidate_id": candidate_id,
            }
            return {**base, "status": "parsed", "output_path": record["output_path"], "page_count": record["page_count"], "parse_record": record}
        except (PdfBenchmarkSelectionError, fitz.FileDataError, RuntimeError, OSError, ValueError) as exc:
            return {**base, "status": "failed", "error": str(exc)}

    def _validate_candidate(self, case: dict[str, Any], candidate: dict[str, Any]) -> None:
        if candidate.get("inventory_status") != "candidate_ready":
            raise PdfBenchmarkSelectionError("candidate is not candidate_ready")
        if candidate.get("sha256") != case.get("sha256"):
            raise PdfBenchmarkSelectionError("selection SHA-256 does not match inventory candidate")
        if candidate.get("insurer_id") != case.get("insurer_id"):
            raise PdfBenchmarkSelectionError("selection insurer_id does not match inventory candidate")
        for field in ("source_url", "source_page_url"):
            value = candidate.get(field)
            host = (urlparse(value).hostname or "").lower() if isinstance(value, str) else ""
            if host.startswith("lifeinsurance."):
                raise PdfBenchmarkSelectionError("life-insurance source is out of scope for the Health benchmark")

    def _parse_pdf(self, case: dict[str, Any], candidate: dict[str, Any], raw_path: Path) -> dict[str, Any]:
        pages: list[dict[str, Any]] = []
        with fitz.open(raw_path) as document:
            for page_number, page in enumerate(document, start=1):
                text = (page.get_text("text") or "").strip()
                pages.append({"page_number": page_number, "text": text, "char_count": len(text)})
        return {
            "schema_version": "1.0",
            "parser_version": PARSER_VERSION,
            "parsed_at": self._utc_now(),
            "benchmark_only": True,
            "benchmark_case_id": case["case_id"],
            "benchmark_candidate_id": case["candidate_id"],
            "insurer_id": candidate["insurer_id"],
            "document_type": candidate["document_type"],
            "sha256": candidate["sha256"],
            "source_url": candidate["source_url"],
            "source_page_url": candidate.get("source_page_url"),
            "relative_archive_path": candidate["raw_pdf_relative_path"],
            "page_count": len(pages),
            "pages": pages,
        }

    @staticmethod
    def parse_id_for(*, candidate_id: str, sha256: str) -> str:
        return "ppbench_" + hashlib.sha256(f"{candidate_id}|{sha256}|{PARSER_VERSION}".encode("utf-8")).hexdigest()[:16]

    def _is_reusable(self, record: dict[str, Any] | None) -> bool:
        if not record or record.get("parse_status") != "parsed" or record.get("parser_version") != PARSER_VERSION:
            return False
        path = record.get("output_path")
        return isinstance(path, str) and (self.base_dir / path).is_file()

    def _resolve_raw_path(self, value: Any) -> Path | None:
        if not isinstance(value, str) or not value.startswith("archive/"):
            return None
        candidate = (self.base_dir / value).resolve()
        root = (self.base_dir / "archive").resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return None
        return candidate

    @staticmethod
    def _validate_selection(selection: dict[str, Any]) -> None:
        if selection.get("schema_version") != "1.0" or selection.get("selection_version") != "1.0":
            raise PdfBenchmarkSelectionError("selection schema/version must be 1.0")
        cases = selection.get("selected_cases")
        if not isinstance(cases, list) or len(cases) != 16:
            raise PdfBenchmarkSelectionError("selection must contain exactly 16 new benchmark cases")
        seen: set[str] = set()
        for case in cases:
            if not isinstance(case, dict):
                raise PdfBenchmarkSelectionError("each selected case must be an object")
            for field in ("case_id", "candidate_id", "insurer_id", "sha256"):
                if not isinstance(case.get(field), str) or not case[field]:
                    raise PdfBenchmarkSelectionError(f"selected case {field} is required")
            if case["case_id"] in seen:
                raise PdfBenchmarkSelectionError("selected case_id values must be unique")
            seen.add(case["case_id"])

    def _load_existing_registry(self) -> dict[str, Any]:
        if not self.parse_registry_path.exists():
            return {"records": []}
        return self._load_object(self.parse_registry_path)

    @staticmethod
    def _load_object(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise
        except json.JSONDecodeError as exc:
            raise PdfBenchmarkSelectionError(f"Invalid JSON: {path}") from exc
        if not isinstance(payload, dict):
            raise PdfBenchmarkSelectionError(f"JSON root must be an object: {path}")
        return payload

    @staticmethod
    def _write_object(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _relative_path(self, path: Path) -> str:
        return str(path.relative_to(self.base_dir)).replace("\\", "/")

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
