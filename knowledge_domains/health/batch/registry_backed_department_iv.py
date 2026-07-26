"""Registry-backed, isolated execution adapter for Department IV.

The existing Department IV engines are reused unchanged. This adapter supplies
explicit Department III artifacts from the registry-backed factory input and
writes all Department IV outputs into the same scoped factory directory.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from knowledge_domains.health.knowledge_manufacturing.knowledge_component_classifier import (
    KnowledgeComponentClassifier,
)
from knowledge_domains.health.knowledge_manufacturing.knowledge_component_normalizer import (
    KnowledgeComponentNormalizerRunner,
)
from knowledge_domains.health.knowledge_manufacturing.knowledge_component_scanner import (
    KnowledgeComponentScannerRunner,
)


UTC = timezone.utc


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class DepartmentIVSelection:
    document_id: str
    document_type: str
    authority_score: int | float | None
    processed_document_path: Path


class RegistryBackedDepartmentIVRunner:
    """Runs scanner, normalizer, and classifier without global-folder discovery."""

    VERSION = "1.0"
    EXECUTION_REGISTRY_FILENAME = "department_iv_execution_registry.json"

    def __init__(
        self,
        *,
        project_root: Path,
        registry_path: Path,
        factory_dir: Path,
    ) -> None:
        self.project_root = project_root.resolve()
        self.registry_path = self._resolve_project_path(registry_path)
        self.factory_dir = self._resolve_project_path(factory_dir)
        self.factory_dir.mkdir(parents=True, exist_ok=True)

        self.scanner_output_dir = self.factory_dir / "knowledge_components"
        self.normalizer_output_dir = self.factory_dir / "normalized_knowledge_components"
        self.classifier_output_dir = self.factory_dir / "classified_knowledge_components"
        self.execution_registry_path = self.factory_dir / self.EXECUTION_REGISTRY_FILENAME

    def run(self, *, entity_id: str, write: bool = True) -> dict[str, Any]:
        selections = self._select_documents(entity_id)
        records: list[dict[str, Any]] = []

        for selection in selections:
            if not write:
                records.append(
                    {
                        "document_id": selection.document_id,
                        "document_type": selection.document_type,
                        "status": "selected",
                        "processed_document_path": self._relative(selection.processed_document_path),
                    }
                )
                continue

            records.append(self._run_document(selection))

        payload = {
            "schema_version": "1.0",
            "execution_version": self.VERSION,
            "generated_at": utc_now(),
            "entity_id": entity_id,
            "registry_path": self._relative(self.registry_path),
            "factory_dir": self._relative(self.factory_dir),
            "department_boundary": "raw_and_classified_components_only_no_insurance_fact_extraction",
            "document_count": len(selections),
            "status_counts": self._status_counts(records),
            "records": records,
            "notes": [
                "Consumes explicit Department III outputs from the registry-backed factory input.",
                "Does not rediscover documents or write to global knowledge/factory folders.",
                "Reuses Department IV scanner, normalizer, and classifier engines unchanged.",
            ],
        }
        if write:
            self.execution_registry_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            payload["execution_registry_path"] = self._relative(self.execution_registry_path)
        return payload

    def _run_document(self, selection: DepartmentIVSelection) -> dict[str, Any]:
        scanner = KnowledgeComponentScannerRunner(project_root=self.project_root, output_dir=self.scanner_output_dir)
        scan_result = scanner.run(selection.processed_document_path)

        normalizer = KnowledgeComponentNormalizerRunner(project_root=self.project_root, output_dir=self.normalizer_output_dir)
        normalize_result = normalizer.run(scan_result["collection_path"])

        classifier = KnowledgeComponentClassifier(project_root=self.project_root, output_dir=self.classifier_output_dir)
        classified_collection, classifier_report = classifier.classify_file(normalize_result["collection_path"])

        return {
            "document_id": selection.document_id,
            "document_type": selection.document_type,
            "authority_score": selection.authority_score,
            "status": "completed",
            "processed_document_path": self._relative(selection.processed_document_path),
            "scanner": {
                "collection_path": self._relative(scan_result["collection_path"]),
                "report_path": self._relative(scan_result["report_path"]),
                "components_created": scan_result["report"].components_created,
                "validation_status": scan_result["report"].validation_status,
            },
            "normalizer": {
                "collection_path": self._relative(normalize_result["collection_path"]),
                "report_path": self._relative(normalize_result["report_path"]),
                "normalized_components_created": normalize_result["report"].normalized_components_created,
                "validation_status": normalize_result["report"].validation_status,
            },
            "classifier": {
                "collection_path": self._relative(Path(classifier_report["classified_collection_path"])),
                "report_path": self._relative(classifier._report_path(classified_collection, classifier_report)),
                "classified_components_created": classifier_report["classified_components_created"],
                "active_components": classifier_report["active_components"],
                "validation_status": classifier_report["validation_status"],
            },
        }

    def _select_documents(self, entity_id: str) -> list[DepartmentIVSelection]:
        if not self.registry_path.exists():
            raise FileNotFoundError(f"Factory input registry not found: {self.registry_path}")
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        selections: list[DepartmentIVSelection] = []
        for record in payload.get("documents", []):
            if entity_id not in (record.get("entity_ids") or []):
                continue
            processing = (record.get("processing_pipeline") or {}).get("document_processing") or {}
            if processing.get("status") != "completed":
                continue
            output_path = processing.get("output_path")
            if not output_path:
                raise ValueError(f"Completed document has no output_path: {record.get('document_id')}")
            processed_path = self._resolve_project_path(Path(output_path))
            if not processed_path.exists():
                raise FileNotFoundError(f"Processed document not found: {processed_path}")
            selections.append(
                DepartmentIVSelection(
                    document_id=str(record["document_id"]),
                    document_type=str(record.get("document_type") or "unknown"),
                    authority_score=record.get("authority_score"),
                    processed_document_path=processed_path,
                )
            )
        return sorted(selections, key=lambda item: (-(item.authority_score or 0), item.document_id))

    def _resolve_project_path(self, value: Path) -> Path:
        return value.resolve() if value.is_absolute() else (self.project_root / value).resolve()

    def _relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.project_root).as_posix()

    @staticmethod
    def _status_counts(records: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in records:
            status = str(record.get("status") or "unknown")
            counts[status] = counts.get(status, 0) + 1
        return counts
