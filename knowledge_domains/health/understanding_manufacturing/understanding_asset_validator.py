"""Understanding Asset Validator v1.0."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class UnderstandingAssetValidator:
    """Validates Understanding Asset assembly without adding new content."""

    def validate_inputs(
        self,
        *,
        meaning_asset: Dict[str, Any],
        learning_primitive_collection: Dict[str, Any],
        learning_path_collection: Dict[str, Any],
    ) -> Tuple[List[str], List[str]]:
        warnings: List[str] = []
        errors: List[str] = []

        if meaning_asset.get("asset_type") != "meaning_asset":
            errors.append("Expected meaning_asset asset_type.")
        if learning_primitive_collection.get("asset_type") != "learning_primitive_collection":
            errors.append("Expected learning_primitive_collection asset_type.")
        if learning_path_collection.get("asset_type") != "learning_path_collection":
            errors.append("Expected learning_path_collection asset_type.")

        concept_ids = {
            meaning_asset.get("concept_id"),
            learning_primitive_collection.get("concept_id"),
            learning_path_collection.get("concept_id"),
        }
        if len({cid for cid in concept_ids if cid}) != 1:
            errors.append("Input concept_id values do not match.")

        if not learning_primitive_collection.get("primitives"):
            errors.append("Learning Primitive Collection has no primitives.")
        if not learning_path_collection.get("paths"):
            errors.append("Learning Path Collection has no paths.")

        primitive_ids = {p.get("primitive_id") for p in learning_primitive_collection.get("primitives", [])}
        for path in learning_path_collection.get("paths", []):
            for step in path.get("steps", []):
                if step.get("primitive_id") not in primitive_ids:
                    errors.append(
                        f"Path {path.get('path_type')} references missing primitive {step.get('primitive_id')}"
                    )

        source_lpc_id = learning_path_collection.get("source_learning_primitive_collection_id")
        if source_lpc_id and source_lpc_id != learning_primitive_collection.get("asset_id"):
            errors.append("Learning Path Collection does not reference supplied Learning Primitive Collection.")

        if not meaning_asset.get("asset_id") and not meaning_asset.get("meaning_asset_id"):
            warnings.append("Meaning Asset does not expose a stable asset_id.")

        return warnings, errors

    def validate_output(self, manufactured_asset: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        warnings: List[str] = []
        errors: List[str] = []

        required_fields = [
            "asset_id",
            "asset_type",
            "concept_id",
            "concept_name",
            "meaning",
            "learning_primitives",
            "learning_paths",
            "learning_outcomes",
            "traceability",
            "factory_signature",
            "department_boundary",
        ]
        for field in required_fields:
            if field not in manufactured_asset:
                errors.append(f"Understanding Asset missing required field: {field}")

        if manufactured_asset.get("asset_type") != "understanding_asset":
            errors.append("Manufactured asset_type must be understanding_asset.")

        if not manufactured_asset.get("learning_outcomes"):
            errors.append("Understanding Asset must include learning_outcomes.")

        if not manufactured_asset.get("learning_primitives", {}).get("primitives"):
            errors.append("Understanding Asset must embed Learning Primitives.")

        if not manufactured_asset.get("learning_paths", {}).get("paths"):
            errors.append("Understanding Asset must embed Learning Paths.")

        signature = manufactured_asset.get("factory_signature", {})
        if not signature.get("deterministic"):
            errors.append("Factory signature must declare deterministic=True.")

        traceability = manufactured_asset.get("traceability", {})
        for field in ["meaning_asset_id", "learning_primitive_collection_id", "learning_path_collection_id"]:
            if not traceability.get(field) or traceability.get(field) == "unknown":
                errors.append(f"Traceability missing {field}.")

        return warnings, errors
