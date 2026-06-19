from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR
from knowledge_domains.health.factory.factory_manager import FactoryManager
from knowledge_domains.health.processing.asset_validation_engine import ProcessedDocumentValidationEngine
from knowledge_domains.health.processing.certification_engine import DepartmentCertificationEngine
from knowledge_domains.health.processing.clause_extractor import ClauseExtractionEngine
from knowledge_domains.health.processing.cross_reference_extractor import CrossReferenceExtractionEngine
from knowledge_domains.health.processing.document_loader import DocumentLoaderEngine
from knowledge_domains.health.processing.document_reader import DocumentReaderEngine
from knowledge_domains.health.processing.processing_models import (
    PROCESSING_ASSET_VERSION,
    PROCESSING_CONTRACT_VERSION,
    ProcessedDocumentAsset,
    ProcessedPage,
    ProcessingManifest,
    ProcessingSource,
    SourceLocation,
    WarningRecord,
    normalize_whitespace,
    stable_id,
    utc_now,
    estimate_reading_time_minutes,
)
from knowledge_domains.health.processing.quality_engine import ProcessedDocumentQualityEngine
from knowledge_domains.health.processing.section_extractor import SectionExtractionEngine
from knowledge_domains.health.processing.table_extractor import TableExtractionEngine


class DocumentProcessingEngine:
    """
    Department III — Document Processing v2.0

    Mission:
        Transform raw evidence into certified Processed Document Assets without
        interpreting insurance knowledge.

    Golden boundary:
        Department III may enrich a document.
        Department III must never interpret a document.
    """

    VERSION = "2.0"
    DEPARTMENT = "department_03_document_processing"

    def __init__(self):
        self.loader = DocumentLoaderEngine()
        self.reader = DocumentReaderEngine()
        self.section_extractor = SectionExtractionEngine()
        self.table_extractor = TableExtractionEngine()
        self.clause_extractor = ClauseExtractionEngine()
        self.cross_ref_extractor = CrossReferenceExtractionEngine()
        self.validation_engine = ProcessedDocumentValidationEngine()
        self.quality_engine = ProcessedDocumentQualityEngine()
        self.certification_engine = DepartmentCertificationEngine()
        self.factory_manager = FactoryManager()
        self.output_dir = BASE_DIR / "knowledge" / "factory" / "processed_documents"
        self.manifest_dir = BASE_DIR / "knowledge" / "factory" / "processing_manifests"
        self.certification_dir = BASE_DIR / "knowledge" / "factory" / "certification_reports"

    def process_job(self, job: dict[str, Any], *, write: bool = True) -> dict[str, Any]:
        if job.get("stage") != "document_processing":
            raise ValueError(f"Unsupported job stage for Document Processing Engine: {job.get('stage')}")

        started = time.perf_counter()
        document_id = job["document_id"]
        self.factory_manager.append_event(
            event_type="document_processing_started",
            payload={"job_id": job.get("job_id"), "document_id": document_id, "engine_version": self.VERSION},
        )

        try:
            loaded = self.loader.load(job)
            read_result = self.reader.read(loaded)
            normalized_pages = self.normalize_pages(read_result.get("pages") or [])
            normalized_text = normalize_whitespace("\n".join(page["text"] for page in normalized_pages))

            sections = self.section_extractor.extract(normalized_text, document_id=document_id)
            tables = self.table_extractor.extract(normalized_text, document_id=document_id)
            clauses = self.clause_extractor.extract(normalized_text, document_id=document_id)
            cross_refs = self.cross_ref_extractor.extract(normalized_text, document_id=document_id)

            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            asset = self.build_asset(
                job=job,
                normalized_text=normalized_text,
                normalized_pages=normalized_pages,
                sections=sections,
                tables=tables,
                clauses=clauses,
                cross_references=cross_refs,
                reader_result=read_result,
                loaded_document=loaded,
                processing_time_ms=elapsed_ms,
            )

            initial_validation = self.validation_engine.validate(asset)
            asset.quality = self.quality_engine.score(asset, initial_validation)
            final_validation = self.validation_engine.validate(asset)
            asset.validation = final_validation
            certification = self.certification_engine.certify(
                document_id=document_id,
                asset_id=asset.asset_id,
                validation=final_validation,
                quality_score=asset.quality.overall_score if asset.quality else 0,
            )

            output_path = self.output_path_for(asset)
            manifest_path = self.manifest_path_for(asset)
            certification_path = self.certification_path_for(asset)
            manifest = self.build_manifest(asset, output_path, final_validation)

            if write:
                self.write_json(output_path, asset.to_dict())
                self.write_json(manifest_path, asdict(manifest))
                self.write_json(certification_path, asdict(certification))

                relative_output = str(output_path.relative_to(BASE_DIR)).replace("\\", "/")
                relative_manifest = str(manifest_path.relative_to(BASE_DIR)).replace("\\", "/")
                relative_certification = str(certification_path.relative_to(BASE_DIR)).replace("\\", "/")
                stage_status = "completed" if certification.certification_status == "certified" else "completed_with_warnings"
                self.factory_manager.mark_stage(
                    document_id=document_id,
                    stage="document_processing",
                    status=stage_status,
                    output_path=relative_output,
                    notes=[
                        "Processed Document Asset manufactured by Department III v2.0",
                        f"quality_score={asset.quality.overall_score if asset.quality else None}",
                        f"certification={certification.certification_status}",
                        f"manifest={relative_manifest}",
                        f"certification_report={relative_certification}",
                    ],
                    write=True,
                )
                self.factory_manager.append_event(
                    event_type="processed_document_certified",
                    payload={
                        "job_id": job.get("job_id"),
                        "document_id": document_id,
                        "asset_id": asset.asset_id,
                        "output_path": relative_output,
                        "manifest_path": relative_manifest,
                        "certification_report_path": relative_certification,
                        "quality_score": asset.quality.overall_score if asset.quality else None,
                        "certification_status": certification.certification_status,
                        "section_count": len(sections),
                        "table_count": len(tables),
                        "clause_count": len(clauses),
                    },
                )

            return {
                "status": "completed",
                "job_id": job.get("job_id"),
                "document_id": document_id,
                "asset_id": asset.asset_id,
                "output_path": str(output_path.relative_to(BASE_DIR)).replace("\\", "/"),
                "manifest_path": str(manifest_path.relative_to(BASE_DIR)).replace("\\", "/"),
                "certification_report_path": str(certification_path.relative_to(BASE_DIR)).replace("\\", "/"),
                "quality_score": asset.quality.overall_score if asset.quality else None,
                "certification_status": certification.certification_status,
                "section_count": len(sections),
                "table_count": len(tables),
                "clause_count": len(clauses),
                "cross_reference_count": len(cross_refs),
                "char_count": len(normalized_text),
            }
        except Exception as exc:
            self.factory_manager.mark_stage(
                document_id=document_id,
                stage="document_processing",
                status="failed",
                notes=[str(exc)],
                output_path=None,
                write=True,
            )
            self.factory_manager.append_event(
                event_type="document_processing_failed",
                payload={"job_id": job.get("job_id"), "document_id": document_id, "error": str(exc)},
            )
            return {"status": "failed", "job_id": job.get("job_id"), "document_id": document_id, "error": str(exc)}

    def normalize_pages(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not pages:
            return [{"page_number": 1, "text": ""}]
        normalized: list[dict[str, Any]] = []
        for idx, page in enumerate(pages, start=1):
            text = normalize_whitespace(str(page.get("text", "")))
            number = page.get("page_number") or idx
            try:
                number = int(number)
            except Exception:
                number = idx
            normalized.append({"page_number": number, "text": text})
        return normalized

    def build_asset(
        self,
        *,
        job: dict[str, Any],
        normalized_text: str,
        normalized_pages: list[dict[str, Any]],
        sections: list[Any],
        tables: list[Any],
        clauses: list[Any],
        cross_references: list[Any],
        reader_result: dict[str, Any],
        loaded_document: dict[str, Any],
        processing_time_ms: float,
    ) -> ProcessedDocumentAsset:
        document_id = job["document_id"]
        asset_id = stable_id("pdoc", f"{document_id}|{job.get('document_hash')}|{self.VERSION}|{PROCESSING_CONTRACT_VERSION}")
        source = ProcessingSource(
            document_id=document_id,
            document_type=job.get("document_type"),
            source_type=job.get("source_type") or job.get("document_type"),
            evidence_role=job.get("evidence_role"),
            authority_score=job.get("authority_score"),
            relative_path=job.get("relative_path"),
            document_hash=job.get("document_hash"),
            source_url=job.get("source_url"),
            evidence_id=job.get("evidence_id"),
            registry_version=job.get("registry_version"),
            document_version=job.get("version") or job.get("document_version"),
        )
        pages = []
        for page in normalized_pages:
            text = page["text"]
            page_number = page["page_number"]
            pages.append(
                ProcessedPage(
                    page_id=stable_id("page", f"{document_id}|{page_number}|{len(text)}"),
                    page_number=page_number,
                    text=text,
                    char_count=len(text),
                    word_count=len(text.split()),
                    line_count=len(text.splitlines()),
                    source_location=SourceLocation(
                        document_id=document_id,
                        page_number=page_number,
                        page_label=str(page_number),
                        start_line=1,
                        end_line=len(text.splitlines()),
                    ),
                    confidence=1.0,
                )
            )

        warnings = self.build_warnings(reader_result.get("warnings", []), document_id=document_id, normalized_text=normalized_text, sections=sections)
        word_count = len(normalized_text.split())
        line_count = len(normalized_text.splitlines())
        statistics = {
            "char_count": len(normalized_text),
            "word_count": word_count,
            "line_count": line_count,
            "page_count": len(pages),
            "section_count": len(sections),
            "table_count": len(tables),
            "clause_count": len(clauses),
            "cross_reference_count": len(cross_references),
            "warning_count": len(warnings),
            "critical_warning_count": sum(1 for warning in warnings if warning.severity == "critical"),
            "estimated_reading_time_minutes": estimate_reading_time_minutes(word_count),
            "source_file_size_bytes": loaded_document.get("file_size_bytes"),
            "reader_type": reader_result.get("reader_type"),
            "json_kind": reader_result.get("json_kind"),
            "processing_time_ms": processing_time_ms,
            "engines_used": self.engines_used(),
            "domain_interpretation_detected": False,
            "department_boundary": "document_structure_only_no_insurance_interpretation",
        }

        return ProcessedDocumentAsset(
            asset_type="processed_document",
            asset_id=asset_id,
            asset_version=PROCESSING_ASSET_VERSION,
            contract_version=PROCESSING_CONTRACT_VERSION,
            processing_engine_version=self.VERSION,
            created_at=utc_now(),
            document_id=document_id,
            source=source,
            normalized_text=normalized_text,
            pages=pages,
            sections=sections,
            tables=tables,
            clauses=clauses,
            cross_references=cross_references,
            statistics=statistics,
            warnings=warnings,
            notes=[
                "Manufactured by Department III — Document Processing v2.0",
                "This asset contains document structure only and no insurance interpretation.",
                "Certified assets are ready for Department IV — Knowledge Manufacturing handover.",
            ],
        )

    def build_warnings(self, raw_warnings: list[Any], *, document_id: str, normalized_text: str, sections: list[Any]) -> list[WarningRecord]:
        warnings: list[WarningRecord] = []
        for idx, item in enumerate(raw_warnings, start=1):
            if isinstance(item, dict):
                warning_type = item.get("warning_type", "reader_warning")
                severity = item.get("severity", "low")
                message = item.get("message", str(item))
            else:
                warning_type = "reader_warning"
                severity = "low"
                message = str(item)
            warnings.append(
                WarningRecord(
                    warning_id=stable_id("warn", f"{document_id}|{warning_type}|{idx}|{message}"),
                    warning_type=warning_type,
                    severity=severity if severity in {"info", "low", "medium", "high", "critical"} else "low",
                    message=message,
                    location=SourceLocation(document_id=document_id),
                )
            )
        if len(normalized_text) == 0:
            warnings.append(
                WarningRecord(
                    warning_id=stable_id("warn", f"{document_id}|empty_text"),
                    warning_type="empty_text",
                    severity="critical",
                    message="No text extracted from source document",
                    location=SourceLocation(document_id=document_id),
                )
            )
        if not sections:
            warnings.append(
                WarningRecord(
                    warning_id=stable_id("warn", f"{document_id}|no_sections"),
                    warning_type="no_sections_extracted",
                    severity="high",
                    message="No sections extracted from document",
                    location=SourceLocation(document_id=document_id),
                )
            )
        return warnings

    def engines_used(self) -> list[dict[str, str]]:
        return [
            {"engine": "DocumentLoaderEngine", "version": getattr(self.loader, "VERSION", "unknown")},
            {"engine": "DocumentReaderEngine", "version": getattr(self.reader, "VERSION", "unknown")},
            {"engine": "SectionExtractionEngine", "version": getattr(self.section_extractor, "VERSION", "unknown")},
            {"engine": "TableExtractionEngine", "version": getattr(self.table_extractor, "VERSION", "unknown")},
            {"engine": "ClauseExtractionEngine", "version": getattr(self.clause_extractor, "VERSION", "unknown")},
            {"engine": "CrossReferenceExtractionEngine", "version": getattr(self.cross_ref_extractor, "VERSION", "unknown")},
            {"engine": "ProcessedDocumentValidationEngine", "version": getattr(self.validation_engine, "VERSION", "unknown")},
            {"engine": "ProcessedDocumentQualityEngine", "version": getattr(self.quality_engine, "VERSION", "unknown")},
            {"engine": "DepartmentCertificationEngine", "version": getattr(self.certification_engine, "VERSION", "unknown")},
        ]

    def build_manifest(self, asset: ProcessedDocumentAsset, output_path: Path, validation: dict[str, Any]) -> ProcessingManifest:
        return ProcessingManifest(
            manifest_type="processing_manifest",
            manifest_id=stable_id("manifest", f"{asset.document_id}|{asset.asset_id}|{self.VERSION}"),
            manifest_version=self.VERSION,
            created_at=utc_now(),
            department=self.DEPARTMENT,
            engine="DocumentProcessingEngine",
            document_id=asset.document_id,
            asset_id=asset.asset_id,
            asset_path=str(output_path.relative_to(BASE_DIR)).replace("\\", "/"),
            quality_score=asset.quality.overall_score if asset.quality else 0.0,
            validation_status=validation.get("status", "unknown"),
            warnings_count=len(asset.warnings),
            critical_warnings_count=sum(1 for warning in asset.warnings if warning.severity == "critical"),
            engines_used=self.engines_used(),
            statistics=asset.statistics,
        )

    def output_path_for(self, asset: ProcessedDocumentAsset) -> Path:
        return self.output_dir / f"{asset.document_id}_{asset.asset_id}_processed_document_v2.json"

    def manifest_path_for(self, asset: ProcessedDocumentAsset) -> Path:
        return self.manifest_dir / f"{asset.document_id}_{asset.asset_id}_processing_manifest.json"

    def certification_path_for(self, asset: ProcessedDocumentAsset) -> Path:
        return self.certification_dir / f"{asset.document_id}_{asset.asset_id}_certification_report.json"

    def write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)

    def load_queue(self, queue_path: Path | None = None) -> dict[str, Any]:
        queue_path = queue_path or (BASE_DIR / "knowledge" / "factory" / "job_queue.json")
        if not queue_path.exists():
            raise FileNotFoundError(f"Factory job queue not found: {queue_path}")
        with queue_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def run_from_queue(self, *, limit: int | None = None, write: bool = True) -> dict[str, Any]:
        queue = self.load_queue()
        jobs = [job for job in queue.get("jobs", []) if job.get("stage") == "document_processing"]
        if limit is not None:
            jobs = jobs[: max(0, limit)]
        results = [self.process_job(job, write=write) for job in jobs]
        return {
            "document_processing_engine_version": self.VERSION,
            "job_count": len(jobs),
            "completed_count": sum(1 for item in results if item.get("status") == "completed"),
            "failed_count": sum(1 for item in results if item.get("status") == "failed"),
            "certified_count": sum(1 for item in results if item.get("certification_status") == "certified"),
            "results": results,
        }
