from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


PIPELINE_STAGES = [
    "registered",
    "document_processing",
    "section_extraction",
    "table_extraction",
    "clause_extraction",
    "knowledge_extraction",
    "ontology_mapping",
    "validation",
    "published",
]

TERMINAL_STATUSES = {"completed", "skipped", "failed"}
ACTIVE_STATUSES = {"pending", "in_progress"}


@dataclass(frozen=True)
class PipelineDefaults:
    """Default status values for a document entering the Knowledge Factory."""

    registered: str = "completed"
    document_processing: str = "pending"
    section_extraction: str = "blocked"
    table_extraction: str = "blocked"
    clause_extraction: str = "blocked"
    knowledge_extraction: str = "blocked"
    ontology_mapping: str = "blocked"
    validation: str = "blocked"
    published: str = "blocked"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_pipeline_status() -> dict[str, Any]:
    defaults = PipelineDefaults()
    return {
        "registered": {
            "status": defaults.registered,
            "updated_at": utc_now(),
            "notes": ["Document exists in Evidence Registry"],
        },
        "document_processing": {
            "status": defaults.document_processing,
            "updated_at": None,
            "notes": [],
        },
        "section_extraction": {
            "status": defaults.section_extraction,
            "updated_at": None,
            "notes": ["Waiting for document processing"],
        },
        "table_extraction": {
            "status": defaults.table_extraction,
            "updated_at": None,
            "notes": ["Waiting for document processing"],
        },
        "clause_extraction": {
            "status": defaults.clause_extraction,
            "updated_at": None,
            "notes": ["Waiting for section extraction"],
        },
        "knowledge_extraction": {
            "status": defaults.knowledge_extraction,
            "updated_at": None,
            "notes": ["Waiting for clauses/sections"],
        },
        "ontology_mapping": {
            "status": defaults.ontology_mapping,
            "updated_at": None,
            "notes": ["Waiting for knowledge extraction"],
        },
        "validation": {
            "status": defaults.validation,
            "updated_at": None,
            "notes": ["Waiting for ontology mapping"],
        },
        "published": {
            "status": defaults.published,
            "updated_at": None,
            "notes": ["Waiting for validation"],
        },
    }


def normalize_pipeline_status(existing: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a complete pipeline status object without overwriting existing stage status."""
    normalized = default_pipeline_status()
    existing = existing or {}

    for stage in PIPELINE_STAGES:
        current = existing.get(stage)
        if isinstance(current, dict):
            normalized[stage].update(current)
        elif isinstance(current, str):
            normalized[stage]["status"] = current
    return normalized


def first_actionable_stage(pipeline: dict[str, Any]) -> str | None:
    """Find the next stage that should receive a factory job."""
    for stage in PIPELINE_STAGES:
        stage_status = pipeline.get(stage, {}).get("status")
        if stage_status == "pending":
            return stage
        if stage_status == "failed":
            return stage
    return None
