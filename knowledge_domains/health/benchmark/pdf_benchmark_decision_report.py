"""Produce a durable, bounded P1.6 decision report from benchmark v1 output.

The report records what the native-text benchmark demonstrates, what it does not
demonstrate, and preserves the provenance of every selected case. It never changes
parser configuration, source governance, product identity, facts, or publication.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PdfBenchmarkDecisionReportError(ValueError):
    """Raised when a P1.6 benchmark report cannot support a decision report."""


class PdfBenchmarkDecisionReport:
    """Create a reproducible decision report from PDF benchmark v1 results."""

    REPORT_VERSION = "1.0"

    def __init__(self, *, base_dir: Path) -> None:
        self.base_dir = base_dir

    @property
    def benchmark_report_path(self) -> Path:
        return self.base_dir / "reports" / "pdf_benchmark_v1_report.json"

    @property
    def decision_report_path(self) -> Path:
        return self.base_dir / "reports" / "pdf_benchmark_v1_decision_report.json"

    def build(self, *, benchmark_report_path: Path | None = None) -> dict[str, Any]:
        source_path = benchmark_report_path or self.benchmark_report_path
        benchmark = self._load_object(source_path)
        self._validate_benchmark(benchmark)
        cases = benchmark["cases"]
        provenance_records = [self._case_provenance(case) for case in cases]
        document_class_summary = self._document_class_summary(cases)
        missing_traits = list(benchmark["benchmark_readiness"].get("missing_declared_traits", []))
        represented = set(benchmark.get("declared_trait_coverage", {}))

        report = {
            "schema_version": "1.0",
            "decision_report_version": self.REPORT_VERSION,
            "generated_at": self._utc_now(),
            "source_benchmark_report_path": self._relative_path(source_path),
            "source_benchmark_manifest_id": benchmark["manifest_id"],
            "cohort": {
                "case_count": benchmark["case_count"],
                "target_case_count": benchmark["target_case_count"],
                "status_counts": benchmark["status_counts"],
                "declared_trait_coverage": benchmark.get("declared_trait_coverage", {}),
                "missing_declared_traits": missing_traits,
            },
            "decision": {
                "parser_strategy_status": "bounded_native_text_baseline_approved",
                "native_text_policy": (
                    "Use native text as the baseline for prose discovery and page-level evidence navigation; "
                    "do not treat it as proof of table reconstruction, reading order, coordinate precision, fact correctness, or currentness."
                ),
                "layout_table_policy": (
                    "For layout-sensitive, multi-column, complex-table, and form-like documents, require manual layout review "
                    "before relying on text order or table-derived field values."
                ),
                "ocr_policy": "deferred_no_represented_ocr_trigger_cases",
                "ocr_rationale": (
                    "The cohort contains no verified poor_native_text or scanned_or_image_heavy case. "
                    "OCR is not justified by this benchmark and must not be added as a default path."
                ),
                "table_reconstruction_policy": "not_proven_do_not_claim",
                "coordinate_evidence_policy": "not_assessed_do_not_claim",
                "automatic_fact_publication_policy": "not_affected",
            },
            "decision_gates": {
                "benchmark_ready_for_unbounded_parser_strategy": bool(benchmark["benchmark_readiness"].get("ready_for_decision")),
                "unbounded_strategy_blockers": missing_traits,
                "next_evidence_required": [
                    "Acquire and classify at least one governed Health PDF with verified poor_native_text or scanned_or_image_heavy traits before reconsidering OCR.",
                    "Run a separate table/reading-order benchmark before approving table reconstruction or layout-sensitive automatic extraction.",
                ],
            },
            "document_class_summary": document_class_summary,
            "case_provenance": provenance_records,
            "limitations": [
                "This is a benchmark decision report, not a product, document identity, currentness, extraction, fact, or publication record.",
                "Null entity_id is intentional for benchmark-only cases without governed product identity; insurer/source provenance is retained instead.",
                "The report makes no claim about OCR quality, table recovery, coordinate evidence precision, or fact extraction accuracy.",
            ],
        }
        self._write_object(self.decision_report_path, report)
        return {"report": report, "report_path": self.decision_report_path}

    @staticmethod
    def _case_provenance(case: dict[str, Any]) -> dict[str, Any]:
        provenance = case.get("parse_provenance") or {}
        return {
            "case_id": case.get("case_id"),
            "benchmark_status": case.get("benchmark_status"),
            "declared_traits": case.get("declared_traits", []),
            "review_reasons": case.get("review_reasons", []),
            "entity_id": provenance.get("entity_id"),
            "insurer_id": provenance.get("insurer_id"),
            "document_type": provenance.get("document_type"),
            "source_document_id": provenance.get("source_document_id"),
            "sha256": provenance.get("sha256"),
            "relative_archive_path": provenance.get("relative_archive_path"),
            "source_url": provenance.get("source_url"),
            "source_page_url": provenance.get("source_page_url"),
            "provenance_status": provenance.get("provenance_status"),
            "benchmark_only": provenance.get("benchmark_only", False),
            "parse_artifact_path": provenance.get("output_path"),
        }

    @staticmethod
    def _document_class_summary(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for case in cases:
            document_type = str((case.get("parse_provenance") or {}).get("document_type") or "unknown")
            grouped[document_type].append(case)
        result: list[dict[str, Any]] = []
        for document_type in sorted(grouped):
            items = grouped[document_type]
            statuses = Counter(str(item.get("benchmark_status")) for item in items)
            review_reasons = sorted({reason for item in items for reason in item.get("review_reasons", [])})
            result.append({
                "document_type": document_type,
                "case_count": len(items),
                "status_counts": dict(sorted(statuses.items())),
                "review_reasons": review_reasons,
                "bounded_recommendation": (
                    "manual_layout_review_required_for_layout_or_table_reliance"
                    if review_reasons else "native_text_baseline_permitted_for_prose_discovery_only"
                ),
            })
        return result

    @staticmethod
    def _validate_benchmark(benchmark: dict[str, Any]) -> None:
        required = ("manifest_id", "case_count", "target_case_count", "benchmark_readiness", "status_counts", "cases")
        missing = [name for name in required if name not in benchmark]
        if missing:
            raise PdfBenchmarkDecisionReportError(f"benchmark report is missing required fields: {missing}")
        if not isinstance(benchmark["cases"], list) or not benchmark["cases"]:
            raise PdfBenchmarkDecisionReportError("benchmark report must contain cases")
        if not isinstance(benchmark["benchmark_readiness"], dict):
            raise PdfBenchmarkDecisionReportError("benchmark_readiness must be an object")

    def _relative_path(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.base_dir.resolve())).replace("\\", "/")
        except ValueError:
            return str(path)

    @staticmethod
    def _load_object(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise
        except json.JSONDecodeError as exc:
            raise PdfBenchmarkDecisionReportError(f"invalid JSON: {path}") from exc
        if not isinstance(payload, dict):
            raise PdfBenchmarkDecisionReportError(f"JSON root must be an object: {path}")
        return payload

    @staticmethod
    def _write_object(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
