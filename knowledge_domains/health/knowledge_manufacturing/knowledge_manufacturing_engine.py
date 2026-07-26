from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR

try:
    from knowledge_domains.health.factory.factory_manager import FactoryManager
except Exception:  # pragma: no cover
    FactoryManager = None  # type: ignore

from knowledge_domains.health.knowledge_manufacturing.concept_recognition_engine import ConceptRecognitionEngine
from knowledge_domains.health.knowledge_manufacturing.concept_review_queue import ConceptReviewQueue
from knowledge_domains.health.knowledge_manufacturing.knowledge_block_builder import KnowledgeBlockBuilder
from knowledge_domains.health.knowledge_manufacturing.knowledge_block_models import (
    KNOWLEDGE_BLOCK_CONTRACT_VERSION,
    KNOWLEDGE_BLOCK_MANUFACTURING_VERSION,
    KnowledgeBlockCollection,
    KnowledgeBlockManufacturingReport,
    stable_id as block_stable_id,
    utc_now as block_utc_now,
)
from knowledge_domains.health.knowledge_manufacturing.knowledge_manufacturing_models import (
    CONCEPT_RECOGNITION_CONTRACT_VERSION,
    KNOWLEDGE_MANUFACTURING_VERSION,
    ConceptRecognitionReport,
    stable_id,
    utc_now,
)


class KnowledgeManufacturingEngine:
    """
    Department IV — Knowledge Manufacturing

    Sprint 2B.1 scope added:
        Knowledge Block Manufacturing.

    Existing Sprint 2B concept recognition remains available.
    """

    VERSION = KNOWLEDGE_MANUFACTURING_VERSION
    DEPARTMENT = "department_04_knowledge_manufacturing"

    def __init__(self):
        self.block_builder = KnowledgeBlockBuilder()
        self.concept_engine = ConceptRecognitionEngine()
        self.review_queue = ConceptReviewQueue()
        self.block_output_dir = BASE_DIR / "knowledge" / "factory" / "knowledge_blocks"
        self.block_report_dir = BASE_DIR / "knowledge" / "factory" / "knowledge_block_reports"
        self.output_dir = BASE_DIR / "knowledge" / "factory" / "concept_recognition_reports"
        self.factory_manager = FactoryManager() if FactoryManager else None

    # ------------------------------------------------------------------
    # Sprint 2B.1 — Knowledge Block Manufacturing
    # ------------------------------------------------------------------
    def manufacture_knowledge_blocks(self, processed_document_path: Path, *, write: bool = True) -> dict[str, Any]:
        started = time.perf_counter()
        processed_document = self.load_json(processed_document_path)
        document_id = processed_document.get("document_id", "unknown_document")
        processed_asset_id = processed_document.get("asset_id")
        source_rel = self.relative_path(processed_document_path)

        self.append_event("knowledge_block_manufacturing_started", {
            "document_id": document_id,
            "processed_document_asset_id": processed_asset_id,
            "source_asset_path": source_rel,
            "engine_version": KNOWLEDGE_BLOCK_MANUFACTURING_VERSION,
        })

        result = self.block_builder.build(processed_document)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        collection = self.build_block_collection(
            processed_document=processed_document,
            processed_document_path=processed_document_path,
            block_result=result,
            processing_time_ms=elapsed_ms,
        )
        collection_path = self.block_collection_output_path(collection)
        report = self.build_block_report(collection=collection, block_result=result, collection_path=collection_path, processing_time_ms=elapsed_ms)
        report_path = self.block_report_output_path(report)

        if write:
            self.write_json(collection_path, collection.to_dict())
            report.collection_path = self.relative_path(collection_path)
            self.write_json(report_path, report.to_dict())
            self.append_event("knowledge_block_collection_published", {
                "document_id": document_id,
                "processed_document_asset_id": processed_asset_id,
                "collection_id": collection.collection_id,
                "collection_path": self.relative_path(collection_path),
                "report_id": report.report_id,
                "report_path": self.relative_path(report_path),
                "blocks_created": len(collection.blocks),
                "quality_score": collection.quality.get("quality_score"),
                "processing_time_ms": elapsed_ms,
            })

        return {
            "status": "completed",
            "stage": "knowledge_blocks",
            "department": self.DEPARTMENT,
            "engine_version": KNOWLEDGE_BLOCK_MANUFACTURING_VERSION,
            "document_id": document_id,
            "processed_document_asset_id": processed_asset_id,
            "collection_id": collection.collection_id,
            "collection_path": self.relative_path(collection_path),
            "report_id": report.report_id,
            "report_path": self.relative_path(report_path),
            "blocks_created": len(collection.blocks),
            "quality_score": collection.quality.get("quality_score"),
            "validation_status": collection.validation.get("status"),
            "processing_time_ms": elapsed_ms,
        }

    def build_block_collection(
        self,
        *,
        processed_document: dict[str, Any],
        processed_document_path: Path,
        block_result: dict[str, Any],
        processing_time_ms: float,
    ) -> KnowledgeBlockCollection:
        document_id = processed_document.get("document_id", "unknown_document")
        processed_asset_id = processed_document.get("asset_id")
        blocks = block_result["blocks"]
        collection_id = block_stable_id("kbc", f"{document_id}|{processed_asset_id}|{KNOWLEDGE_BLOCK_CONTRACT_VERSION}|{len(blocks)}")
        statistics = dict(block_result["statistics"])
        statistics["processing_time_ms"] = processing_time_ms
        statistics["source_asset_path"] = self.relative_path(processed_document_path)
        validation_status = block_result.get("validation_status", "passed")
        return KnowledgeBlockCollection(
            asset_type="knowledge_block_collection",
            collection_id=collection_id,
            collection_version="1.0",
            contract_version=KNOWLEDGE_BLOCK_CONTRACT_VERSION,
            created_at=block_utc_now(),
            department=self.DEPARTMENT,
            engine="KnowledgeManufacturingEngine.KnowledgeBlockBuilder",
            document_id=document_id,
            processed_document_asset_id=processed_asset_id,
            source_asset_path=self.relative_path(processed_document_path),
            blocks=blocks,
            statistics=statistics,
            quality={
                "quality_score": block_result["quality_score"],
                "confidence": round(block_result["quality_score"] / 100, 4),
                "warning_count": len(block_result.get("warnings", [])),
            },
            validation={
                "status": validation_status,
                "gates": {
                    "all_sections_assigned": block_result["orphan_paragraphs"] == 0,
                    "no_duplicate_blocks": block_result["duplicate_blocks"] == 0,
                    "provenance_present": True,
                    "no_semantic_interpretation": True,
                    "ready_for_concept_recognition": validation_status in {"passed", "warning"},
                },
            },
        )

    def build_block_report(
        self,
        *,
        collection: KnowledgeBlockCollection,
        block_result: dict[str, Any],
        collection_path: Path,
        processing_time_ms: float,
    ) -> KnowledgeBlockManufacturingReport:
        return KnowledgeBlockManufacturingReport(
            report_type="knowledge_block_manufacturing_report",
            report_id=block_stable_id("kbmr", f"{collection.document_id}|{collection.collection_id}|{KNOWLEDGE_BLOCK_MANUFACTURING_VERSION}"),
            report_version=KNOWLEDGE_BLOCK_MANUFACTURING_VERSION,
            created_at=block_utc_now(),
            department=self.DEPARTMENT,
            engine="KnowledgeManufacturingEngine.KnowledgeBlockBuilder",
            document_id=collection.document_id,
            processed_document_asset_id=collection.processed_document_asset_id,
            collection_id=collection.collection_id,
            collection_path=self.relative_path(collection_path),
            blocks_created=len(collection.blocks),
            orphan_paragraphs=block_result["orphan_paragraphs"],
            duplicate_blocks=block_result["duplicate_blocks"],
            tables_attached=block_result["tables_attached"],
            cross_references_preserved=block_result["cross_references_preserved"],
            warnings=block_result.get("warnings", []),
            quality_score=block_result["quality_score"],
            validation_status=block_result.get("validation_status", "passed"),
            statistics={**collection.statistics, "processing_time_ms": processing_time_ms},
        )

    def block_collection_output_path(self, collection: KnowledgeBlockCollection) -> Path:
        return self.block_output_dir / f"{collection.document_id}_{collection.processed_document_asset_id}_{collection.collection_id}_knowledge_block_collection.json"

    def block_report_output_path(self, report: KnowledgeBlockManufacturingReport) -> Path:
        return self.block_report_dir / f"{report.document_id}_{report.processed_document_asset_id}_{report.report_id}_knowledge_block_manufacturing_report.json"

    # ------------------------------------------------------------------
    # Existing Sprint 2B — Concept Recognition
    # ------------------------------------------------------------------
    def process_processed_document(self, processed_document_path: Path, *, write: bool = True) -> dict[str, Any]:
        started = time.perf_counter()
        processed_document = self.load_json(processed_document_path)
        document_id = processed_document.get("document_id", "unknown_document")
        processed_asset_id = processed_document.get("asset_id")

        self.append_event("knowledge_manufacturing_concept_recognition_started", {
            "document_id": document_id,
            "processed_document_asset_id": processed_asset_id,
            "source_asset_path": self.relative_path(processed_document_path),
            "engine_version": self.VERSION,
        })

        recognition_result = self.concept_engine.recognize(processed_document)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        report = self.build_report(
            processed_document=processed_document,
            processed_document_path=processed_document_path,
            recognition_result=recognition_result,
            processing_time_ms=elapsed_ms,
        )

        output_path = self.output_path_for(report)
        queue_result = {"added_count": 0, "item_count": 0, "pending_count": 0, "path": None}
        if write:
            self.write_json(output_path, report.to_dict())
            queue_result = self.review_queue.append_items(report.review_items)
            self.append_event("concept_recognition_report_published", {
                "document_id": report.document_id,
                "processed_document_asset_id": report.processed_document_asset_id,
                "report_id": report.report_id,
                "report_path": self.relative_path(output_path),
                "recognized_count": len(report.recognized_concepts),
                "review_required_count": len(report.review_items),
                "unknown_count": len(report.unknown_concepts),
                "processing_time_ms": elapsed_ms,
            })

        return {
            "status": "completed",
            "stage": "concept_recognition",
            "department": self.DEPARTMENT,
            "engine_version": self.VERSION,
            "document_id": report.document_id,
            "processed_document_asset_id": report.processed_document_asset_id,
            "report_id": report.report_id,
            "report_path": self.relative_path(output_path),
            "recognized_count": len(report.recognized_concepts),
            "auto_approved_count": report.statistics["auto_approved_count"],
            "review_required_count": report.statistics["review_required_count"],
            "unknown_count": len(report.unknown_concepts),
            "review_queue": queue_result,
            "processing_time_ms": elapsed_ms,
        }

    def build_report(
        self,
        *,
        processed_document: dict[str, Any],
        processed_document_path: Path,
        recognition_result: dict[str, Any],
        processing_time_ms: float,
    ) -> ConceptRecognitionReport:
        recognized = recognition_result["recognized_concepts"]
        unknowns = recognition_result["unknown_concepts"]
        review_items = recognition_result["review_items"]
        document_id = processed_document.get("document_id", "unknown_document")
        asset_id = processed_document.get("asset_id")
        auto_count = sum(1 for item in recognized if item.decision == "auto_approved")
        review_count = sum(1 for item in recognized if item.decision == "review_required")
        statistics = {
            "recognized_count": len(recognized),
            "auto_approved_count": auto_count,
            "review_required_count": review_count,
            "unknown_count": len(unknowns),
            "review_queue_count": len(review_items),
            "source_section_count": len(processed_document.get("sections", [])),
            "source_clause_count": len(processed_document.get("clauses", [])),
            "processing_time_ms": processing_time_ms,
            "department_boundary": "concept_recognition_only_no_knowledge_atom_manufacturing",
            "next_sprint": "Sprint 2C - Semantic Canonicalization",
        }
        return ConceptRecognitionReport(
            report_type="concept_recognition_report",
            report_id=stable_id("crr", f"{document_id}|{asset_id}|{self.VERSION}|{CONCEPT_RECOGNITION_CONTRACT_VERSION}"),
            report_version=self.VERSION,
            contract_version=CONCEPT_RECOGNITION_CONTRACT_VERSION,
            created_at=utc_now(),
            department=self.DEPARTMENT,
            engine="KnowledgeManufacturingEngine.ConceptRecognition",
            document_id=document_id,
            processed_document_asset_id=asset_id,
            source_asset_path=self.relative_path(processed_document_path),
            recognized_concepts=recognized,
            unknown_concepts=unknowns,
            review_items=review_items,
            statistics=statistics,
            thresholds={
                "auto_approve_threshold": self.concept_engine.AUTO_APPROVE_THRESHOLD,
                "review_threshold": self.concept_engine.REVIEW_THRESHOLD,
            },
        )

    def output_path_for(self, report: ConceptRecognitionReport) -> Path:
        return self.output_dir / f"{report.document_id}_{report.processed_document_asset_id}_{report.report_id}_concept_recognition_report.json"

    def latest_processed_documents(self) -> list[Path]:
        directory = BASE_DIR / "knowledge" / "factory" / "processed_documents"
        if not directory.exists():
            return []
        return sorted(directory.glob("*_processed_document_v2.json"), key=lambda path: path.stat().st_mtime, reverse=True)

    def run(self, *, processed_document_path: Path | None = None, limit: int | None = None, write: bool = True, stage: str = "knowledge_blocks") -> dict[str, Any]:
        paths = [processed_document_path] if processed_document_path else self.latest_processed_documents()
        paths = [path for path in paths if path is not None]
        if limit is not None:
            paths = paths[: max(0, limit)]

        if stage in {"knowledge_blocks", "blocks", "2b1"}:
            results = [self.manufacture_knowledge_blocks(path, write=write) for path in paths]
            normalized_stage = "knowledge_blocks"
        elif stage in {"concept_recognition", "recognition", "2b"}:
            results = [self.process_processed_document(path, write=write) for path in paths]
            normalized_stage = "concept_recognition"
        else:
            raise ValueError(f"Unsupported stage: {stage}. Use knowledge_blocks or concept_recognition.")

        return {
            "knowledge_manufacturing_engine_version": self.VERSION,
            "stage": normalized_stage,
            "input_count": len(paths),
            "completed_count": sum(1 for item in results if item.get("status") == "completed"),
            "results": results,
        }

    def append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if not self.factory_manager:
            return
        try:
            self.factory_manager.append_event(event_type=event_type, payload=payload)
        except Exception:
            return

    def load_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Processed Document Asset not found: {path}")
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)

    def relative_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(BASE_DIR)).replace("\\", "/")
        except Exception:
            return str(path).replace("\\", "/")
