from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .processing_models import ProcessedDocumentAsset, WarningRecord, SourceLocation, stable_id


class ProcessedDocumentValidationEngine:
    """
    Department III — Document Processing
    Engine: Processed Document Validation Engine

    Responsibility:
        Validate Processed Document Assets before publication.
    """

    VERSION = "2.0"

    REQUIRED_TOP_LEVEL = [
        "asset_type",
        "asset_id",
        "asset_version",
        "contract_version",
        "processing_engine_version",
        "created_at",
        "document_id",
        "source",
        "normalized_text",
        "pages",
        "sections",
        "statistics",
    ]

    QUALITY_GATES = [
        "identity",
        "provenance",
        "structural_completeness",
        "normalization",
        "cross_references",
        "quality_metrics",
        "validation",
        "observability",
        "performance",
        "factory_readiness",
    ]

    def validate(self, asset: ProcessedDocumentAsset) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        gate_results: dict[str, Any] = {}

        asset_dict = asset.to_dict()
        missing = [field for field in self.REQUIRED_TOP_LEVEL if not asset_dict.get(field)]
        if missing:
            errors.append(f"Missing required top-level fields: {', '.join(missing)}")

        gate_results["identity"] = self.validate_identity(asset)
        gate_results["provenance"] = self.validate_provenance(asset)
        gate_results["structural_completeness"] = self.validate_structure(asset)
        gate_results["normalization"] = self.validate_normalization(asset)
        gate_results["cross_references"] = self.validate_cross_references(asset)
        gate_results["quality_metrics"] = self.validate_quality_metrics(asset)
        gate_results["validation"] = {"passed": len(missing) == 0, "notes": [] if not missing else missing}
        gate_results["observability"] = self.validate_observability(asset)
        gate_results["performance"] = self.validate_performance(asset)
        gate_results["factory_readiness"] = self.validate_factory_readiness(asset)

        for gate, result in gate_results.items():
            if not result.get("passed"):
                if gate in {"identity", "provenance", "validation", "factory_readiness"}:
                    errors.extend([f"{gate}: {note}" for note in result.get("notes", [])])
                else:
                    warnings.extend([f"{gate}: {note}" for note in result.get("notes", [])])

        duplicate_ids = self.find_duplicate_ids(asset)
        if duplicate_ids:
            errors.append(f"Duplicate IDs detected: {', '.join(sorted(duplicate_ids)[:10])}")

        critical_warning_count = sum(1 for item in asset.warnings if item.severity == "critical")
        if critical_warning_count:
            errors.append(f"Critical warnings present: {critical_warning_count}")

        status = "passed" if not errors else "failed"
        passed_gates = [gate for gate, result in gate_results.items() if result.get("passed")]
        failed_gates = [gate for gate, result in gate_results.items() if not result.get("passed")]

        return {
            "validation_engine_version": self.VERSION,
            "status": status,
            "passed_gates": passed_gates,
            "failed_gates": failed_gates,
            "gate_results": gate_results,
            "errors": errors,
            "warnings": warnings,
        }

    def validate_identity(self, asset: ProcessedDocumentAsset) -> dict[str, Any]:
        notes = []
        if not asset.asset_id or not asset.asset_id.startswith("pdoc_"):
            notes.append("Processed document asset_id must exist and start with pdoc_")
        for collection_name in ("pages", "sections", "tables", "clauses", "cross_references"):
            for item in getattr(asset, collection_name):
                id_value = getattr(item, f"{collection_name[:-1]}_id", None)
                if collection_name == "cross_references":
                    id_value = getattr(item, "reference_id", None)
                if not id_value:
                    notes.append(f"{collection_name} item missing stable ID")
        return {"passed": not notes, "notes": notes}

    def validate_provenance(self, asset: ProcessedDocumentAsset) -> dict[str, Any]:
        notes = []
        for collection_name in ("pages", "sections", "tables", "clauses"):
            for item in getattr(asset, collection_name):
                loc = getattr(item, "source_location", None)
                if loc is None or loc.document_id != asset.document_id:
                    notes.append(f"{collection_name} item missing valid source_location")
        if not asset.source.relative_path:
            notes.append("source.relative_path missing")
        return {"passed": not notes, "notes": notes}

    def validate_structure(self, asset: ProcessedDocumentAsset) -> dict[str, Any]:
        notes = []
        if not asset.pages:
            notes.append("no pages manufactured")
        if not asset.sections:
            notes.append("no sections manufactured")
        return {"passed": not notes, "notes": notes}

    def validate_normalization(self, asset: ProcessedDocumentAsset) -> dict[str, Any]:
        notes = []
        text = asset.normalized_text or ""
        if "\r" in text:
            notes.append("carriage returns remain in normalized text")
        if "\t" in text:
            notes.append("tab characters remain in normalized text")
        if len(text.strip()) == 0:
            notes.append("normalized text is empty")
        return {"passed": not notes, "notes": notes}

    def validate_cross_references(self, asset: ProcessedDocumentAsset) -> dict[str, Any]:
        # Cross references may not exist in every doc; pass if detector ran and field exists.
        return {"passed": isinstance(asset.cross_references, list), "notes": []}

    def validate_quality_metrics(self, asset: ProcessedDocumentAsset) -> dict[str, Any]:
        notes = []
        if asset.quality is None:
            notes.append("quality score missing")
        if not asset.statistics:
            notes.append("statistics missing")
        return {"passed": not notes, "notes": notes}

    def validate_observability(self, asset: ProcessedDocumentAsset) -> dict[str, Any]:
        notes = []
        if "engines_used" not in asset.statistics:
            notes.append("statistics.engines_used missing")
        return {"passed": not notes, "notes": notes}

    def validate_performance(self, asset: ProcessedDocumentAsset) -> dict[str, Any]:
        notes = []
        if "processing_time_ms" not in asset.statistics:
            notes.append("statistics.processing_time_ms missing")
        return {"passed": not notes, "notes": notes}

    def validate_factory_readiness(self, asset: ProcessedDocumentAsset) -> dict[str, Any]:
        notes = []
        if asset.asset_type != "processed_document":
            notes.append("asset_type must be processed_document")
        if not asset.contract_version:
            notes.append("contract_version missing")
        if asset.statistics.get("domain_interpretation_detected"):
            notes.append("Department III boundary violation: domain interpretation detected")
        return {"passed": not notes, "notes": notes}

    def find_duplicate_ids(self, asset: ProcessedDocumentAsset) -> set[str]:
        ids: list[str] = [asset.asset_id]
        ids.extend(page.page_id for page in asset.pages)
        ids.extend(section.section_id for section in asset.sections)
        ids.extend(table.table_id for table in asset.tables)
        ids.extend(clause.clause_id for clause in asset.clauses)
        ids.extend(ref.reference_id for ref in asset.cross_references)
        seen: set[str] = set()
        dupes: set[str] = set()
        for item in ids:
            if item in seen:
                dupes.add(item)
            seen.add(item)
        return dupes
