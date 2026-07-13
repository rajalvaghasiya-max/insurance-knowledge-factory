"""P1.6 benchmark harness for existing immutable PDF parse artifacts.

This module measures native-text parse characteristics only.  It deliberately does
not infer table recovery, coordinate evidence, OCR quality, or fact correctness.
"""
from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BENCHMARK_VERSION = "1.0"
SUPPORTED_TRAITS = {
    "policy_wording",
    "customer_information_sheet",
    "brochure",
    "product_benefit_table",
    "proposal_form",
    "claim_form",
    "prospectus",
    "exclusion_annexure",
    "long_document",
    "potential_table_or_form_layout",
    "layout_sensitive_candidate",
    "scanned_or_image_heavy",
    "multi_column",
    "complex_table",
    "repeated_header_footer",
    "poor_native_text",
}


class PdfBenchmarkError(ValueError):
    """Raised for invalid benchmark definitions or artifacts."""


@dataclass(frozen=True)
class BenchmarkPaths:
    manifest: Path
    report: Path
    registry: Path


class PdfBenchmarkV1:
    """Evaluate manifest-selected parse artifacts without changing source evidence."""

    def __init__(self, *, base_dir: Path) -> None:
        self.base_dir = base_dir

    @property
    def parse_registry_path(self) -> Path:
        return self.base_dir / "registry" / "pdf_parse_registry.json"

    @property
    def default_paths(self) -> BenchmarkPaths:
        return BenchmarkPaths(
            manifest=self.base_dir / "examples" / "pdf_benchmark" / "p1_6_benchmark_manifest.v1.json",
            report=self.base_dir / "reports" / "pdf_benchmark_v1_report.json",
            registry=self.base_dir / "registry" / "pdf_benchmark_v1_registry.json",
        )

    def build(self, *, manifest_path: Path | None = None) -> dict[str, Any]:
        paths = self.default_paths
        manifest_path = manifest_path or paths.manifest
        manifest = self._load_object(manifest_path)
        self._validate_manifest(manifest)
        parse_records = self._load_object(self.parse_registry_path).get("records", [])
        if not isinstance(parse_records, list):
            raise PdfBenchmarkError("pdf_parse_registry.records must be a list")
        by_parse_id = {str(record.get("parse_id")): record for record in parse_records if isinstance(record, dict)}

        results = [self._evaluate_case(case, by_parse_id) for case in manifest["cases"]]
        results.sort(key=lambda item: item["case_id"])
        counts = Counter(item["benchmark_status"] for item in results)
        trait_coverage = Counter()
        for case in manifest["cases"]:
            for trait in case["declared_traits"]:
                trait_coverage[trait] += 1

        report = {
            "schema_version": "1.0",
            "benchmark_version": BENCHMARK_VERSION,
            "manifest_id": manifest["manifest_id"],
            "generated_at": self._utc_now(),
            "case_count": len(results),
            "target_case_count": manifest["target_case_count"],
            "benchmark_readiness": self._readiness(manifest, trait_coverage),
            "status_counts": {
                "native_text_usable": counts.get("native_text_usable", 0),
                "native_text_review_required": counts.get("native_text_review_required", 0),
                "blocked": counts.get("blocked", 0),
            },
            "declared_trait_coverage": dict(sorted(trait_coverage.items())),
            "cases": results,
            "limitations": [
                "This benchmark evaluates existing native-text parse artifacts only.",
                "Table reconstruction, coordinate evidence precision, OCR quality, and field extraction accuracy are not assessed by this version.",
                "A native_text_usable result is not a publication, fact-correctness, or currentness decision.",
                "This cohort does not represent verified poor_native_text or scanned_or_image_heavy documents; OCR remains deferred.",
                "Benchmark-only cases preserve insurer/source provenance but must not infer product identity when entity_id is null.",
            ],
        }
        registry = {
            "schema_version": "1.0",
            "benchmark_version": BENCHMARK_VERSION,
            "generated_at": self._utc_now(),
            "records": results,
        }
        self._write_object(paths.report, report)
        self._write_object(paths.registry, registry)
        return {"report": report, "report_path": paths.report, "registry_path": paths.registry}

    def _evaluate_case(self, case: dict[str, Any], by_parse_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
        parse_id = case["parse_id"]
        base = {
            "case_id": case["case_id"],
            "parse_id": parse_id,
            "declared_traits": case["declared_traits"],
            "manual_review_expectation": case["manual_review_expectation"],
            "notes": case.get("notes", ""),
        }
        parse = by_parse_id.get(parse_id)
        if not parse:
            return {**base, "benchmark_status": "blocked", "blockers": ["parse_record_not_found"], "metrics": {}}
        artifact_path = self._resolve_processed_path(parse.get("output_path"))
        if artifact_path is None or not artifact_path.is_file():
            return {**base, "benchmark_status": "blocked", "blockers": ["parse_artifact_not_found"], "metrics": {}}
        artifact = self._load_object(artifact_path)
        pages = artifact.get("pages")
        if not isinstance(pages, list) or not pages:
            return {**base, "benchmark_status": "blocked", "blockers": ["invalid_page_structure"], "metrics": {}}
        texts = [page.get("text", "") if isinstance(page, dict) and isinstance(page.get("text", ""), str) else "" for page in pages]
        char_counts = [len(text) for text in texts]
        total_chars = sum(char_counts)
        nonempty_ratio = sum(1 for count in char_counts if count > 0) / len(char_counts)
        median_chars = float(statistics.median(char_counts))
        repeated = self._repeated_lines(texts)
        native_status = "native_text_usable"
        reasons: list[str] = []
        if total_chars < 500 or nonempty_ratio < 0.8:
            native_status = "blocked"
            reasons.append("insufficient_native_text")
        elif median_chars < 80 or "scanned_or_image_heavy" in case["declared_traits"] or "poor_native_text" in case["declared_traits"]:
            native_status = "native_text_review_required"
            reasons.append("native_text_quality_review_required")
        elif "complex_table" in case["declared_traits"] or "multi_column" in case["declared_traits"]:
            native_status = "native_text_review_required"
            reasons.append("layout_sensitive_document")
        return {
            **base,
            "benchmark_status": native_status,
            "blockers": reasons if native_status == "blocked" else [],
            "review_reasons": reasons if native_status == "native_text_review_required" else [],
            "parse_provenance": {
                # entity_id is intentionally nullable for benchmark-only documents.
                # Insurer/source identity is retained without inferring product identity.
                "entity_id": parse.get("entity_id"),
                "insurer_id": parse.get("insurer_id"),
                "product_name": parse.get("product_name"),
                "document_type": parse.get("document_type"),
                "source_document_id": parse.get("source_document_id"),
                "sha256": parse.get("sha256"),
                "relative_archive_path": parse.get("relative_archive_path"),
                "source_url": parse.get("source_url"),
                "source_page_url": parse.get("source_page_url"),
                "provenance_status": parse.get("provenance_status"),
                "benchmark_only": bool(parse.get("benchmark_only", False)),
                "benchmark_case_id": parse.get("benchmark_case_id"),
                "benchmark_candidate_id": parse.get("benchmark_candidate_id"),
                "output_path": parse.get("output_path"),
            },
            "metrics": {
                "page_count": len(texts),
                "total_characters": total_chars,
                "nonempty_page_ratio": round(nonempty_ratio, 4),
                "median_characters_per_page": median_chars,
                "repeated_line_count": len(repeated),
                "repeated_line_samples": repeated[:5],
                "table_recovery": "not_assessed",
                "coordinate_evidence_precision": "not_assessed",
                "ocr_quality": "not_assessed",
            },
        }

    @staticmethod
    def _repeated_lines(texts: list[str]) -> list[str]:
        required_pages = max(2, round(len(texts) * 0.2))
        page_line_sets: list[set[str]] = []
        for text in texts:
            lines = set()
            for line in text.splitlines():
                line = " ".join(line.split())
                if 8 <= len(line) <= 180:
                    lines.add(line)
            page_line_sets.append(lines)
        count = Counter(line for lines in page_line_sets for line in lines)
        return sorted(line for line, occurrences in count.items() if occurrences >= required_pages)

    @staticmethod
    def _readiness(manifest: dict[str, Any], trait_coverage: Counter[str]) -> dict[str, Any]:
        minimum = manifest["target_case_count"]
        missing = sorted(SUPPORTED_TRAITS.difference(trait_coverage))
        return {
            "ready_for_decision": len(manifest["cases"]) >= minimum and not missing,
            "case_count_sufficient": len(manifest["cases"]) >= minimum,
            "missing_declared_traits": missing,
            "decision_rule": "No parser-strategy decision may be made until target case count and all declared document traits are represented.",
        }

    @staticmethod
    def _validate_manifest(manifest: dict[str, Any]) -> None:
        if manifest.get("schema_version") != "1.0":
            raise PdfBenchmarkError("manifest.schema_version must be 1.0")
        if manifest.get("benchmark_version") != BENCHMARK_VERSION:
            raise PdfBenchmarkError("manifest.benchmark_version is unsupported")
        if not isinstance(manifest.get("manifest_id"), str) or not manifest["manifest_id"]:
            raise PdfBenchmarkError("manifest.manifest_id is required")
        target = manifest.get("target_case_count")
        if not isinstance(target, int) or target < 20 or target > 30:
            raise PdfBenchmarkError("manifest.target_case_count must be between 20 and 30")
        cases = manifest.get("cases")
        if not isinstance(cases, list) or not cases:
            raise PdfBenchmarkError("manifest.cases must be a non-empty list")
        case_ids = set()
        for case in cases:
            if not isinstance(case, dict):
                raise PdfBenchmarkError("each benchmark case must be an object")
            case_id = case.get("case_id")
            if not isinstance(case_id, str) or not case_id or case_id in case_ids:
                raise PdfBenchmarkError("case_id must be unique and non-empty")
            case_ids.add(case_id)
            if not isinstance(case.get("parse_id"), str) or not case["parse_id"]:
                raise PdfBenchmarkError(f"{case_id}.parse_id is required")
            traits = case.get("declared_traits")
            if not isinstance(traits, list) or not traits or not all(isinstance(item, str) for item in traits):
                raise PdfBenchmarkError(f"{case_id}.declared_traits must be non-empty strings")
            unknown = set(traits).difference(SUPPORTED_TRAITS)
            if unknown:
                raise PdfBenchmarkError(f"{case_id}.declared_traits contain unsupported values: {sorted(unknown)}")
            if case.get("manual_review_expectation") not in {"required", "not_required", "unknown"}:
                raise PdfBenchmarkError(f"{case_id}.manual_review_expectation is invalid")

    def _resolve_processed_path(self, value: Any) -> Path | None:
        if not isinstance(value, str) or not value.startswith("processed/"):
            return None
        candidate = (self.base_dir / value).resolve()
        root = (self.base_dir / "processed").resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return None
        return candidate

    @staticmethod
    def _load_object(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise
        except json.JSONDecodeError as exc:
            raise PdfBenchmarkError(f"invalid JSON: {path}") from exc
        if not isinstance(payload, dict):
            raise PdfBenchmarkError(f"JSON root must be object: {path}")
        return payload

    @staticmethod
    def _write_object(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
