"""
PolicyScna Department V — Understanding Asset Manufacturing Line v1.0

Consumes:
    meaning_asset + learning_primitive_collection + learning_path_collection

Manufactures:
    understanding_asset

Boundary:
    Packages existing Department V assets only. It does not create new
    educational content, personalize, recommend, reason, or generate conversations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from factory_sdk import (
    CertificationResult,
    CertificationStatus,
    FactoryProductionLine,
    ProductionLineContract,
    QualityWarning,
)

from .understanding_asset_builder import UnderstandingAssetBuilder
from .understanding_asset_validator import UnderstandingAssetValidator


DEPARTMENT_BOUNDARY = "meaning_primitives_paths_to_understanding_asset_only_no_new_content_no_personalization"


class UnderstandingAssetManufacturingLine(FactoryProductionLine):
    """Manufactures certified Understanding Assets from Department V inputs."""

    contract = ProductionLineContract(
        engine_name="UnderstandingAssetManufacturingLine",
        department="department_05_understanding_manufacturing",
        production_line="understanding_asset_manufacturing",
        consumes="department_05_asset_bundle",
        manufactures="understanding_asset",
        customer_department="department_06_reasoning_manufacturing",
        engine_version="1.0",
        rules_version="understanding_asset_rules_v1.0",
        schema_version="understanding_asset_v1.0",
        deterministic=True,
        certification_required=True,
        department_boundary=DEPARTMENT_BOUNDARY,
    )

    def __init__(
        self,
        *,
        meaning_asset_path: Path,
        learning_primitive_asset_path: Path,
        learning_path_asset_path: Path,
        output_dir: Path,
        factory_version: str = "1.0",
    ) -> None:
        self.meaning_asset_path = Path(meaning_asset_path)
        self.learning_primitive_asset_path = Path(learning_primitive_asset_path)
        self.learning_path_asset_path = Path(learning_path_asset_path)
        super().__init__(input_path=self.learning_path_asset_path, output_dir=Path(output_dir), factory_version=factory_version)

    def load(self) -> Dict[str, Any]:
        return {
            "asset_type": self.contract.consumes,
            "meaning_asset_path": str(self.meaning_asset_path),
            "learning_primitive_asset_path": str(self.learning_primitive_asset_path),
            "learning_path_asset_path": str(self.learning_path_asset_path),
            "meaning_asset": self._load_json(self.meaning_asset_path),
            "learning_primitive_collection": self._load_json(self.learning_primitive_asset_path),
            "learning_path_collection": self._load_json(self.learning_path_asset_path),
        }

    def validate_input(self, raw_input: Dict[str, Any]) -> None:
        super().validate_input(raw_input)
        if raw_input.get("asset_type") != self.contract.consumes:
            raise ValueError(f"Expected bundled input asset_type={self.contract.consumes}.")
        warnings, errors = UnderstandingAssetValidator().validate_inputs(
            meaning_asset=raw_input.get("meaning_asset", {}),
            learning_primitive_collection=raw_input.get("learning_primitive_collection", {}),
            learning_path_collection=raw_input.get("learning_path_collection", {}),
        )
        if errors:
            raise ValueError("; ".join(errors))

    def manufacture(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        builder = UnderstandingAssetBuilder(
            engine_version=self.contract.engine_version,
            rules_version=self.contract.rules_version,
            schema_version=self.contract.schema_version,
            factory_version=self.factory_version,
            department=self.contract.department,
            production_line=self.contract.production_line,
            department_boundary=self.contract.department_boundary,
        )
        return builder.build(
            meaning_asset=raw_input["meaning_asset"],
            learning_primitive_collection=raw_input["learning_primitive_collection"],
            learning_path_collection=raw_input["learning_path_collection"],
        )

    def quality_check(
        self, raw_input: Dict[str, Any], manufactured_asset: Dict[str, Any]
    ) -> Tuple[float, List[QualityWarning], List[str]]:
        quality_score, warnings, errors = super().quality_check(raw_input, manufactured_asset)
        validator_warnings, validator_errors = UnderstandingAssetValidator().validate_output(manufactured_asset)
        for message in validator_warnings:
            warnings.append(QualityWarning(type="understanding_asset_validation", severity="low", message=message))
        errors.extend(validator_errors)
        if errors:
            quality_score = min(quality_score, 60.0)
        elif warnings:
            quality_score = min(quality_score, 95.0)
        return quality_score, warnings, errors

    def certify(self, raw_input: Dict[str, Any], manufactured_asset: Dict[str, Any]) -> CertificationResult:
        certification = super().certify(raw_input, manufactured_asset)
        gates_passed = list(certification.gates_passed)
        gates_failed = list(certification.gates_failed)
        errors = list(certification.errors)
        warnings = list(certification.warnings)

        traceability = manufactured_asset.get("traceability", {})
        if traceability.get("meaning_asset_id") and traceability.get("learning_primitive_collection_id") and traceability.get("learning_path_collection_id"):
            gates_passed.append("traceability_preserved")
        else:
            gates_failed.append("traceability_preserved")

        if manufactured_asset.get("learning_primitives", {}).get("count", 0) > 0:
            gates_passed.append("learning_primitives_packaged")
        else:
            gates_failed.append("learning_primitives_packaged")

        if manufactured_asset.get("learning_paths", {}).get("count", 0) > 0:
            gates_passed.append("learning_paths_packaged")
        else:
            gates_failed.append("learning_paths_packaged")

        if manufactured_asset.get("learning_outcomes"):
            gates_passed.append("learning_outcomes_aggregated")
        else:
            gates_failed.append("learning_outcomes_aggregated")

        if manufactured_asset.get("factory_signature", {}).get("production_line") == "UnderstandingAssetManufacturingLine":
            gates_passed.append("factory_signature_present")
        else:
            gates_failed.append("factory_signature_present")

        if all(gate not in gates_failed for gate in [
            "traceability_preserved",
            "learning_primitives_packaged",
            "learning_paths_packaged",
            "learning_outcomes_aggregated",
            "factory_signature_present",
        ]):
            gates_passed.append("understanding_asset_contract_preserved")
        else:
            gates_failed.append("understanding_asset_contract_preserved")

        status = CertificationStatus.PASSED
        if errors or gates_failed:
            status = CertificationStatus.FAILED
        elif warnings or certification.quality_score < 90:
            status = CertificationStatus.NEEDS_REVIEW

        return CertificationResult(
            validation_status=status,
            quality_score=certification.quality_score,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
            warnings=warnings,
            errors=errors,
        )

    def build_statistics(
        self,
        raw_input: Dict[str, Any],
        manufactured_asset: Dict[str, Any],
        certification: CertificationResult,
    ) -> Dict[str, Any]:
        base = super().build_statistics(raw_input, manufactured_asset, certification)
        base.update(
            {
                "concept_id": manufactured_asset.get("concept_id"),
                "concept_name": manufactured_asset.get("concept_name"),
                "meaning_asset_id": manufactured_asset.get("traceability", {}).get("meaning_asset_id"),
                "learning_primitive_collection_id": manufactured_asset.get("traceability", {}).get("learning_primitive_collection_id"),
                "learning_path_collection_id": manufactured_asset.get("traceability", {}).get("learning_path_collection_id"),
                "primitive_count": manufactured_asset.get("learning_primitives", {}).get("count"),
                "path_count": manufactured_asset.get("learning_paths", {}).get("count"),
                "learning_outcome_count": len(manufactured_asset.get("learning_outcomes", [])),
                "related_concept_count": len(manufactured_asset.get("relationships", {}).get("related_concepts", [])),
            }
        )
        return base

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Input asset not found: {path}")
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
