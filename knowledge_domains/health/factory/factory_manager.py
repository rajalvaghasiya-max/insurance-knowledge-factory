from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR
from knowledge_domains.health.evidence.evidence_registry import EvidenceRegistry
from knowledge_domains.health.factory.pipeline_status import (
    PIPELINE_STAGES,
    first_actionable_stage,
    normalize_pipeline_status,
)


@dataclass(frozen=True)
class FactoryPaths:
    factory_dir: Path
    queue_path: Path
    event_log_path: Path
    registry_path: Path


class FactoryManager:
    """
    Factory Manager v0.1

    Department:
        Production Control

    Purpose:
        Coordinate the Knowledge Factory pipeline without doing the work itself.

    What this class does:
        - Reads the Evidence Registry.
        - Adds/normalizes pipeline status for each registered document.
        - Plans the next jobs required by the factory.
        - Writes a job queue and event log.

    What this class deliberately does NOT do:
        - Parse documents.
        - Extract insurance facts.
        - Call LLMs.
        - Map ontology.
        - Validate product knowledge.

    This keeps orchestration separate from document processing.
    """

    VERSION = "0.1"

    STAGE_TO_ENGINE = {
        "document_processing": "Document Processing Engine",
        "section_extraction": "Section Extraction Engine",
        "table_extraction": "Table Extraction Engine",
        "clause_extraction": "Clause Extraction Engine",
        "knowledge_extraction": "Knowledge Manufacturing Engine",
        "ontology_mapping": "Ontology Mapping Engine",
        "validation": "Validation Engine",
        "published": "Knowledge Publisher",
    }

    def __init__(self, registry_path: Path | None = None, factory_dir: Path | None = None):
        self.registry = EvidenceRegistry(registry_path=registry_path)
        self.paths = self.get_factory_paths(self.registry.paths.registry_path, factory_dir=factory_dir)

    def get_factory_paths(self, registry_path: Path, factory_dir: Path | None = None) -> FactoryPaths:
        """Resolve factory paths inside the project root.

        Command-line callers commonly provide a relative --factory-dir.  Resolve it
        against BASE_DIR once so every downstream engine writes absolute paths and
        can safely derive project-relative provenance paths.
        """
        configured_dir = Path(factory_dir) if factory_dir is not None else BASE_DIR / "knowledge" / "factory"
        if not configured_dir.is_absolute():
            configured_dir = BASE_DIR / configured_dir
        factory_dir = configured_dir.resolve()
        return FactoryPaths(
            factory_dir=factory_dir,
            queue_path=factory_dir / "job_queue.json",
            event_log_path=factory_dir / "event_log.jsonl",
            registry_path=registry_path,
        )

    def initialize_factory(self, *, write: bool = True) -> dict[str, Any]:
        """Attach factory pipeline status to every active registry document."""
        registry = self.registry.load_registry()
        documents = registry.get("documents", [])

        initialized_count = 0
        for doc in documents:
            before = json.dumps(doc.get("processing_pipeline", {}), sort_keys=True)
            doc["processing_pipeline"] = normalize_pipeline_status(doc.get("processing_pipeline"))
            after = json.dumps(doc.get("processing_pipeline", {}), sort_keys=True)
            if before != after:
                initialized_count += 1

        registry["factory"] = {
            "factory_manager_version": self.VERSION,
            "initialized_at": self.utc_now(),
            "pipeline_stages": PIPELINE_STAGES,
        }

        if write:
            self.write_registry(registry)
            self.append_event(
                event_type="factory_initialized",
                payload={
                    "document_count": len(documents),
                    "initialized_count": initialized_count,
                },
            )

        return {
            "factory_manager_version": self.VERSION,
            "document_count": len(documents),
            "initialized_count": initialized_count,
            "registry_path": str(self.paths.registry_path),
        }

    def plan_jobs(
        self,
        *,
        entity_id: str | None = None,
        stage: str | None = None,
        limit: int | None = None,
        write: bool = True,
    ) -> dict[str, Any]:
        """Create a deterministic job queue for pending factory work."""
        registry = self.registry.load_registry()
        documents = registry.get("documents", [])
        jobs: list[dict[str, Any]] = []

        for doc in documents:
            if doc.get("status") != "active":
                continue
            if entity_id and entity_id not in doc.get("entity_ids", []):
                continue

            doc["processing_pipeline"] = normalize_pipeline_status(doc.get("processing_pipeline"))
            next_stage = first_actionable_stage(doc["processing_pipeline"])

            if not next_stage:
                continue
            if stage and next_stage != stage:
                continue

            jobs.append(self.build_job_record(doc, next_stage))

        jobs = sorted(
            jobs,
            key=lambda item: (
                item["stage_priority"],
                -item["authority_score"],
                item["relative_path"],
            ),
        )

        if limit is not None:
            jobs = jobs[: max(0, limit)]

        queue = {
            "queue_version": self.VERSION,
            "generated_at": self.utc_now(),
            "entity_id": entity_id,
            "stage": stage,
            "job_count": len(jobs),
            "jobs": jobs,
        }

        if write:
            self.paths.factory_dir.mkdir(parents=True, exist_ok=True)
            with self.paths.queue_path.open("w", encoding="utf-8") as file:
                json.dump(queue, file, indent=2, ensure_ascii=False)
            self.write_registry(registry)
            self.append_event(
                event_type="job_queue_planned",
                payload={
                    "entity_id": entity_id,
                    "stage": stage,
                    "job_count": len(jobs),
                },
            )

        return queue

    def mark_stage(
        self,
        *,
        document_id: str,
        stage: str,
        status: str,
        notes: list[str] | None = None,
        output_path: str | None = None,
        write: bool = True,
    ) -> dict[str, Any]:
        """Update one document's pipeline stage. Useful after future engines finish work."""
        if stage not in PIPELINE_STAGES:
            raise ValueError(f"Unknown pipeline stage: {stage}")

        registry = self.registry.load_registry()
        target_doc = None
        for doc in registry.get("documents", []):
            if doc.get("document_id") == document_id:
                target_doc = doc
                break

        if target_doc is None:
            raise ValueError(f"Document not found in registry: {document_id}")

        target_doc["processing_pipeline"] = normalize_pipeline_status(target_doc.get("processing_pipeline"))
        target_doc["processing_pipeline"][stage] = {
            "status": status,
            "updated_at": self.utc_now(),
            "notes": notes or [],
            "output_path": output_path,
        }

        self.unlock_next_stages(target_doc["processing_pipeline"], completed_stage=stage, status=status)

        if write:
            self.write_registry(registry)
            self.append_event(
                event_type="stage_marked",
                payload={
                    "document_id": document_id,
                    "stage": stage,
                    "status": status,
                    "output_path": output_path,
                },
            )

        return {
            "document_id": document_id,
            "stage": stage,
            "status": status,
            "output_path": output_path,
        }

    def unlock_next_stages(self, pipeline: dict[str, Any], *, completed_stage: str, status: str) -> None:
        if status != "completed":
            return

        unlock_map = {
            "document_processing": ["section_extraction", "table_extraction"],
            "section_extraction": ["clause_extraction"],
            "table_extraction": [],
            "clause_extraction": ["knowledge_extraction"],
            "knowledge_extraction": ["ontology_mapping"],
            "ontology_mapping": ["validation"],
            "validation": ["published"],
        }

        for next_stage in unlock_map.get(completed_stage, []):
            if pipeline.get(next_stage, {}).get("status") == "blocked":
                pipeline[next_stage]["status"] = "pending"
                pipeline[next_stage]["updated_at"] = self.utc_now()
                pipeline[next_stage]["notes"] = [f"Unlocked after {completed_stage} completed"]

    def build_job_record(self, doc: dict[str, Any], stage: str) -> dict[str, Any]:
        job_seed = f"{doc.get('document_id')}|{stage}|{doc.get('document_hash')}"
        return {
            "job_id": self.stable_id("job", job_seed),
            "document_id": doc.get("document_id"),
            "entity_ids": doc.get("entity_ids", []),
            "stage": stage,
            "stage_priority": PIPELINE_STAGES.index(stage),
            "assigned_engine": self.STAGE_TO_ENGINE.get(stage, "Unknown Engine"),
            "artifact_type": doc.get("artifact_type"),
            "document_type": doc.get("document_type"),
            "evidence_role": doc.get("evidence_role"),
            "authority_score": doc.get("authority_score", 0),
            "relative_path": doc.get("relative_path"),
            "path": doc.get("path"),
            "document_hash": doc.get("document_hash"),
            "source_document_id": doc.get("source_document_id"),
            "source_type": doc.get("source_type"),
            "source_url": doc.get("source_url"),
            "source_page_url": doc.get("source_page_url"),
            "raw_evidence_relative_path": doc.get("raw_evidence_relative_path"),
            "raw_evidence_path": doc.get("raw_evidence_path"),
            "parse_id": doc.get("parse_id"),
            "parse_artifact_hash": doc.get("parse_artifact_hash"),
            "parser_version": doc.get("parser_version"),
            "quality_audit_id": doc.get("quality_audit_id"),
            "quality_status": doc.get("quality_status"),
            "processing_input_hash": doc.get("processing_input_hash"),
            "registry_version": self.registry.VERSION,
            "status": "planned",
            "planned_at": self.utc_now(),
            "reason": self.job_reason(doc, stage),
        }

    def job_reason(self, doc: dict[str, Any], stage: str) -> str:
        engine = self.STAGE_TO_ENGINE.get(stage, "factory engine")
        return (
            f"{engine} is required for {doc.get('document_type')} "
            f"({doc.get('evidence_role')}) before downstream manufacturing can continue."
        )

    def write_registry(self, registry: dict[str, Any]) -> None:
        self.paths.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with self.paths.registry_path.open("w", encoding="utf-8") as file:
            json.dump(registry, file, indent=2, ensure_ascii=False)

    def append_event(self, *, event_type: str, payload: dict[str, Any]) -> None:
        self.paths.factory_dir.mkdir(parents=True, exist_ok=True)
        event = {
            "event_id": self.stable_id("evt", f"{event_type}|{self.utc_now()}|{json.dumps(payload, sort_keys=True)}"),
            "event_type": event_type,
            "created_at": self.utc_now(),
            "payload": payload,
        }
        with self.paths.event_log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")

    def stable_id(self, prefix: str, value: str) -> str:
        digest = hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:20]
        return f"{prefix}_{digest}"

    def utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
