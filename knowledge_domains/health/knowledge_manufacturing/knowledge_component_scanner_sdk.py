from __future__ import annotations

"""
Department IV — Knowledge Component Scanner SDK Adapter v1.0

Purpose:
    Run the existing KnowledgeComponentScanner through the Factory SDK lifecycle
    without changing the current scanner implementation.

Design:
    - This file is a parallel SDK-based scanner.
    - It delegates scanner-specific manufacturing logic to KnowledgeComponentScanner.
    - Factory SDK owns lifecycle, report, certification, event, and publish flow.
    - Original knowledge_component_scanner.py remains untouched.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from factory_sdk.factory_production_line import FactoryProductionLine
from factory_sdk.factory_sdk_models import (
    CertificationResult,
    CertificationStatus,
    ProductionLineContract,
    QualityWarning,
)

from knowledge_domains.health.knowledge_manufacturing.knowledge_component_scanner import (
    KnowledgeComponentScanner,
)
from knowledge_domains.health.knowledge_manufacturing.knowledge_component_scanner_models import (
    COMPONENT_COLLECTION_CONTRACT_VERSION,
    SCANNER_VERSION,
)


DEPARTMENT_BOUNDARY = "raw_knowledge_components_only_no_semantic_insurance_interpretation"


class KnowledgeComponentScannerSDK(FactoryProductionLine):
    """SDK-managed adapter for KnowledgeComponentScanner.

    This class intentionally does not reimplement component-scanning rules.
    It only adapts the existing scanner to the standard FactoryProductionLine
    lifecycle.
    """

    contract = ProductionLineContract(
        engine_name="KnowledgeComponentScannerSDK",
        department="department_04_knowledge_manufacturing",
        production_line="knowledge_component_scanning",
        consumes="processed_document",
        manufactures="knowledge_component_collection",
        customer_department="knowledge_component_normalization",
        engine_version=SCANNER_VERSION,
        rules_version="knowledge_component_scanner_rules_v1.0",
        schema_version=COMPONENT_COLLECTION_CONTRACT_VERSION,
        deterministic=True,
        certification_required=True,
        department_boundary=DEPARTMENT_BOUNDARY,
    )

    def __init__(self, *, input_path: Path, output_dir: Path, factory_version: str = "1.0") -> None:
        super().__init__(input_path=input_path, output_dir=output_dir, factory_version=factory_version)
        self._scanner = KnowledgeComponentScanner()
        self._legacy_report: Dict[str, Any] | None = None

    def validate_input(self, raw_input: Dict[str, Any]) -> None:
        super().validate_input(raw_input)
        if not (raw_input.get("asset_type") or raw_input.get("document_id")):
            raise ValueError("Input does not look like a processed document asset: missing asset_type/document_id.")
        sections = raw_input.get("sections") or raw_input.get("processed_sections") or []
        if not isinstance(sections, list):
            raise ValueError("Processed document sections must be a list.")

    def manufacture(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        collection, legacy_report = self._scanner.scan(
            raw_input,
            source_asset_path=str(self.input_path),
        )
        self._legacy_report = legacy_report.to_dict()

        asset = collection.to_dict()

        # SDK contract fields. These are adapter-level metadata and do not alter
        # scanner business behavior.
        asset["asset_id"] = asset.get("collection_id")
        asset["schema_version"] = asset.get("contract_version", COMPONENT_COLLECTION_CONTRACT_VERSION)
        asset["engine_version"] = SCANNER_VERSION
        asset["rules_version"] = self.contract.rules_version
        asset["factory_version"] = self.factory_version
        asset["manufactured_by"] = self.contract.engine_name
        asset["input_assets"] = [str(self.input_path)]
        asset["source_evidence"] = self._source_evidence_ids(asset)
        asset["department_boundary"] = self.contract.department_boundary
        asset["persistence"] = "versioned"
        asset["certification"] = {"status": "pending_sdk_certification"}

        return asset

    def quality_check(
        self,
        raw_input: Dict[str, Any],
        manufactured_asset: Dict[str, Any],
    ) -> Tuple[float, List[QualityWarning], List[str]]:
        quality_score, warnings, errors = super().quality_check(raw_input, manufactured_asset)

        components = manufactured_asset.get("components", [])
        validation = manufactured_asset.get("validation", {})
        statistics = manufactured_asset.get("statistics", {})

        if not components:
            errors.append("Scanner produced zero components.")
            quality_score = min(quality_score, 0.0)

        if validation.get("status") not in {"passed", "needs_review", "manufactured_with_warnings"}:
            warnings.append(
                QualityWarning(
                    type="legacy_validation_not_passed",
                    severity="medium",
                    message=f"Legacy scanner validation status: {validation.get('status')}",
                )
            )
            quality_score = min(quality_score, 85.0)

        missing_provenance = [
            component.get("component_id", "unknown")
            for component in components
            if not component.get("source")
        ]
        if missing_provenance:
            errors.append(f"{len(missing_provenance)} component(s) missing source provenance.")
            quality_score = min(quality_score, 50.0)

        if statistics.get("component_type_counts") is None and statistics.get("type_counts") is None:
            warnings.append(
                QualityWarning(
                    type="missing_type_count_statistics",
                    severity="low",
                    message="Scanner statistics do not expose component type counts under a standard key.",
                )
            )
            quality_score = min(quality_score, 95.0)

        # Prefer the legacy scanner's own quality score if present and lower.
        legacy_quality = (manufactured_asset.get("quality") or {}).get("quality_score")
        if isinstance(legacy_quality, (int, float)):
            quality_score = min(float(quality_score), float(legacy_quality))

        return round(float(quality_score), 2), warnings, errors

    def certify(self, raw_input: Dict[str, Any], manufactured_asset: Dict[str, Any]) -> CertificationResult:
        certification = super().certify(raw_input, manufactured_asset)
        manufactured_asset["certification"] = certification.to_dict()
        return certification

    def build_statistics(
        self,
        raw_input: Dict[str, Any],
        manufactured_asset: Dict[str, Any],
        certification: CertificationResult,
    ) -> Dict[str, Any]:
        components = manufactured_asset.get("components", [])
        legacy_report = self._legacy_report or {}
        legacy_stats = manufactured_asset.get("statistics", {}) or {}

        return {
            "input_asset_type": raw_input.get("asset_type"),
            "output_asset_type": manufactured_asset.get("asset_type"),
            "components_created": len(components),
            "source_sections_processed": legacy_report.get("source_sections_processed"),
            "source_tables_processed": legacy_report.get("source_tables_processed"),
            "duplicate_components": legacy_report.get("duplicate_components"),
            "noise_components": legacy_report.get("noise_components"),
            "cross_references_preserved": legacy_report.get("cross_references_preserved"),
            "legacy_validation_status": legacy_report.get("validation_status"),
            "legacy_quality_score": legacy_report.get("quality_score"),
            "legacy_statistics": legacy_stats,
            "contract": self.contract.to_dict(),
            "gates_passed": certification.gates_passed,
            "gates_failed": certification.gates_failed,
        }

    @staticmethod
    def _source_evidence_ids(asset: Dict[str, Any]) -> List[str]:
        evidence_ids: set[str] = set()
        for component in asset.get("components", []):
            source = component.get("source") or {}
            section_id = source.get("section_id")
            if section_id:
                evidence_ids.add(str(section_id))
        return sorted(evidence_ids)


class KnowledgeComponentScannerSDKRunner:
    """File-oriented runner for scripts/run_knowledge_component_scanner_sdk.py."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root).resolve()
        self.output_dir = self.project_root / "knowledge" / "factory" / "knowledge_components_sdk"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, processed_document_path: str | Path) -> Dict[str, Path]:
        processed_path = Path(processed_document_path)
        if not processed_path.is_absolute():
            processed_path = self.project_root / processed_path
        scanner = KnowledgeComponentScannerSDK(
            input_path=processed_path,
            output_dir=self.output_dir,
        )
        return scanner.run()
