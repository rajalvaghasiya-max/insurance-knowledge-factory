"""
PolicyScna Department V — Learning Path Manufacturing Line v1.0

Consumes:
    learning_primitive_collection

Manufactures:
    learning_path_collection

Boundary:
    Manufactures deterministic learning paths only. It does not create new
    learning content, personalize, recommend, or generate conversations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from factory_sdk import (
    CertificationResult,
    CertificationStatus,
    FactoryProductionLine,
    ProductionLineContract,
    QualityWarning,
    stable_hash,
)

from .learning_path_builder import LearningPathBuilder
from .learning_path_models import LearningPathCollection
from .learning_path_validator import LearningPathValidator


DEPARTMENT_BOUNDARY = "learning_primitives_to_learning_paths_only_no_new_content_no_personalization"


class LearningPathManufacturingLine(FactoryProductionLine):
    """Manufactures Learning Path Collections from Learning Primitive Collections."""

    contract = ProductionLineContract(
        engine_name="LearningPathManufacturingLine",
        department="department_05_understanding_manufacturing",
        production_line="learning_path_manufacturing",
        consumes="learning_primitive_collection",
        manufactures="learning_path_collection",
        customer_department="understanding_asset_manufacturing",
        engine_version="1.0",
        rules_version="learning_path_rules_v1.0",
        schema_version="learning_path_collection_v1.0",
        deterministic=True,
        certification_required=True,
        department_boundary=DEPARTMENT_BOUNDARY,
    )

    def validate_input(self, raw_input: Dict[str, Any]) -> None:
        super().validate_input(raw_input)
        if raw_input.get("asset_type") != self.contract.consumes:
            raise ValueError(
                f"Expected input asset_type={self.contract.consumes}, got {raw_input.get('asset_type')}"
            )
        if not raw_input.get("concept_id"):
            raise ValueError("Learning Primitive Collection must include concept_id.")
        if not raw_input.get("concept_name"):
            raise ValueError("Learning Primitive Collection must include concept_name.")
        if not raw_input.get("primitives"):
            raise ValueError("Learning Primitive Collection must include primitives.")

    def manufacture(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        builder = LearningPathBuilder(rules_version=self.contract.rules_version)
        paths = builder.build_paths(raw_input)

        payload_for_id = {
            "concept_id": raw_input.get("concept_id"),
            "source_learning_primitive_collection_id": raw_input.get("asset_id"),
            "rules_version": self.contract.rules_version,
            "paths": [path.to_dict() for path in paths],
        }
        asset_id = stable_hash(payload_for_id, prefix="lpathc")

        collection = LearningPathCollection(
            asset_id=asset_id,
            asset_type=self.contract.manufactures,
            collection_id=asset_id,
            collection_version="1.0",
            schema_version=self.contract.schema_version,
            department_boundary=self.contract.department_boundary,
            concept_id=raw_input.get("concept_id"),
            concept_name=raw_input.get("concept_name"),
            source_learning_primitive_collection_id=raw_input.get("asset_id", "unknown"),
            source_learning_primitive_asset_type=raw_input.get("asset_type", "unknown"),
            paths=paths,
            notes=[
                "Learning Paths are deterministic sequences of existing Learning Primitives.",
                "No new educational content, personalized advice, or final conversation is manufactured in this asset.",
            ],
        )
        return collection.to_dict()

    def quality_check(
        self, raw_input: Dict[str, Any], manufactured_asset: Dict[str, Any]
    ) -> Tuple[float, List[QualityWarning], List[str]]:
        quality_score, warnings, errors = super().quality_check(raw_input, manufactured_asset)

        validator = LearningPathValidator()
        validator_warnings, validator_errors = validator.validate(raw_input, manufactured_asset)
        for message in validator_warnings:
            warnings.append(QualityWarning(type="learning_path_validation", severity="low", message=message))
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

        paths = manufactured_asset.get("paths", [])
        primitive_ids = {p.get("primitive_id") for p in raw_input.get("primitives", [])}

        if all(path.get("learning_goal") for path in paths):
            gates_passed.append("path_learning_goals_present")
        else:
            gates_failed.append("path_learning_goals_present")

        if all(path.get("target_persona") for path in paths):
            gates_passed.append("target_personas_present")
        else:
            gates_failed.append("target_personas_present")

        if self._all_steps_reference_existing_primitives(paths, primitive_ids):
            gates_passed.append("steps_reference_existing_primitives")
        else:
            gates_failed.append("steps_reference_existing_primitives")

        if self._all_paths_have_ordered_steps(paths):
            gates_passed.append("ordered_steps_valid")
        else:
            gates_failed.append("ordered_steps_valid")

        if self._no_duplicate_steps(paths):
            gates_passed.append("no_duplicate_primitives_within_path")
        else:
            gates_failed.append("no_duplicate_primitives_within_path")

        expected_path_types = {
            "quick_understanding",
            "claim_understanding",
            "buying_decision",
            "advisor_teaching",
            "deep_learning",
        }
        actual_path_types = {path.get("path_type") for path in paths}
        if expected_path_types.issubset(actual_path_types):
            gates_passed.append("standard_paths_manufactured")
        else:
            gates_failed.append("standard_paths_manufactured")

        if all(gate not in gates_failed for gate in [
            "path_learning_goals_present",
            "target_personas_present",
            "steps_reference_existing_primitives",
            "ordered_steps_valid",
            "no_duplicate_primitives_within_path",
            "standard_paths_manufactured",
        ]):
            gates_passed.append("learning_path_contract_preserved")
        else:
            gates_failed.append("learning_path_contract_preserved")

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
        paths = manufactured_asset.get("paths", [])
        primitive_type_counts: Dict[str, int] = {}
        path_step_counts: Dict[str, int] = {}
        total_steps = 0

        for path in paths:
            path_type = path.get("path_type", "unknown")
            steps = path.get("steps", [])
            path_step_counts[path_type] = len(steps)
            total_steps += len(steps)
            for step in steps:
                primitive_type = step.get("primitive_type", "unknown")
                primitive_type_counts[primitive_type] = primitive_type_counts.get(primitive_type, 0) + 1

        base.update(
            {
                "concept_id": manufactured_asset.get("concept_id"),
                "concept_name": manufactured_asset.get("concept_name"),
                "source_learning_primitive_collection_id": manufactured_asset.get(
                    "source_learning_primitive_collection_id"
                ),
                "primitive_count": len(raw_input.get("primitives", [])),
                "path_count": len(paths),
                "total_path_steps": total_steps,
                "path_types": [path.get("path_type") for path in paths],
                "path_step_counts": path_step_counts,
                "primitive_usage_counts": primitive_type_counts,
            }
        )
        return base

    @staticmethod
    def _all_steps_reference_existing_primitives(paths: List[Dict[str, Any]], primitive_ids: set) -> bool:
        return all(step.get("primitive_id") in primitive_ids for path in paths for step in path.get("steps", []))

    @staticmethod
    def _all_paths_have_ordered_steps(paths: List[Dict[str, Any]]) -> bool:
        for path in paths:
            step_numbers = [step.get("step_number") for step in path.get("steps", [])]
            if step_numbers != list(range(1, len(step_numbers) + 1)):
                return False
        return True

    @staticmethod
    def _no_duplicate_steps(paths: List[Dict[str, Any]]) -> bool:
        for path in paths:
            primitive_ids = [step.get("primitive_id") for step in path.get("steps", [])]
            if len(primitive_ids) != len(set(primitive_ids)):
                return False
        return True
