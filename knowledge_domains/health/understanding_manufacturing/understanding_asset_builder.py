"""Understanding Asset Builder v1.0."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set

from factory_sdk import stable_hash

from .understanding_asset_models import (
    UnderstandingAsset,
    UnderstandingAssetFactorySignature,
    UnderstandingAssetTraceability,
)


class UnderstandingAssetBuilder:
    """Assembles one certified Understanding Asset from Department V inputs."""

    def __init__(
        self,
        *,
        engine_version: str,
        rules_version: str,
        schema_version: str,
        factory_version: str,
        sdk_version: str = "1.3",
        department: str = "department_05_understanding_manufacturing",
        production_line: str = "understanding_asset_manufacturing",
        department_boundary: str,
    ) -> None:
        self.engine_version = engine_version
        self.rules_version = rules_version
        self.schema_version = schema_version
        self.factory_version = factory_version
        self.sdk_version = sdk_version
        self.department = department
        self.production_line = production_line
        self.department_boundary = department_boundary

    def build(
        self,
        *,
        meaning_asset: Dict[str, Any],
        learning_primitive_collection: Dict[str, Any],
        learning_path_collection: Dict[str, Any],
    ) -> Dict[str, Any]:
        concept_id = meaning_asset.get("concept_id") or learning_primitive_collection.get("concept_id")
        concept_name = meaning_asset.get("canonical_name") or meaning_asset.get("concept_name") or learning_primitive_collection.get("concept_name")

        learning_outcomes = self._build_learning_outcomes(
            learning_primitive_collection.get("primitives", []),
            learning_path_collection.get("paths", []),
        )

        meaning_summary = self._meaning_summary(meaning_asset)
        primitive_summary = self._primitive_summary(learning_primitive_collection)
        path_summary = self._path_summary(learning_path_collection)
        relationships = self._relationships(meaning_asset, learning_primitive_collection)
        traceability = self._traceability(meaning_asset, learning_primitive_collection, learning_path_collection)

        payload_for_id = {
            "concept_id": concept_id,
            "meaning_asset_id": traceability.meaning_asset_id,
            "learning_primitive_collection_id": traceability.learning_primitive_collection_id,
            "learning_path_collection_id": traceability.learning_path_collection_id,
            "rules_version": self.rules_version,
            "schema_version": self.schema_version,
        }
        asset_id = stable_hash(payload_for_id, prefix="ua")

        signature = UnderstandingAssetFactorySignature(
            factory="PolicyScna Knowledge Factory",
            department=self.department,
            production_line="UnderstandingAssetManufacturingLine",
            engine_version=self.engine_version,
            rules_version=self.rules_version,
            schema_version=self.schema_version,
            factory_version=self.factory_version,
            sdk_version=self.sdk_version,
            deterministic=True,
        )

        asset = UnderstandingAsset(
            asset_id=asset_id,
            asset_type="understanding_asset",
            schema_version=self.schema_version,
            asset_version="1.0",
            department_boundary=self.department_boundary,
            concept_id=concept_id,
            concept_name=concept_name,
            meaning=meaning_summary,
            learning_primitives=primitive_summary,
            learning_paths=path_summary,
            learning_outcomes=learning_outcomes,
            relationships=relationships,
            traceability=traceability,
            factory_signature=signature,
            notes=[
                "Understanding Assets package certified meaning, learning primitives, and learning paths.",
                "No new educational content, personalized advice, recommendation, or conversation is manufactured in this asset.",
            ],
        )
        return asset.to_dict()

    @staticmethod
    def _meaning_summary(meaning_asset: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "asset_id": meaning_asset.get("asset_id") or meaning_asset.get("meaning_asset_id"),
            "asset_type": meaning_asset.get("asset_type"),
            "canonical_name": meaning_asset.get("canonical_name") or meaning_asset.get("concept_name"),
            "core_meaning": meaning_asset.get("core_meaning"),
            "business_purpose": meaning_asset.get("business_purpose"),
            "calculation_basis": meaning_asset.get("calculation_basis"),
            "trigger": meaning_asset.get("trigger"),
            "confidence": meaning_asset.get("confidence"),
        }

    @staticmethod
    def _primitive_summary(collection: Dict[str, Any]) -> Dict[str, Any]:
        primitives = collection.get("primitives", [])
        return {
            "asset_id": collection.get("asset_id"),
            "asset_type": collection.get("asset_type"),
            "schema_version": collection.get("schema_version"),
            "count": len(primitives),
            "primitive_types": [p.get("primitive_type") for p in primitives],
            "primitives": primitives,
        }

    @staticmethod
    def _path_summary(collection: Dict[str, Any]) -> Dict[str, Any]:
        paths = collection.get("paths", [])
        return {
            "asset_id": collection.get("asset_id"),
            "asset_type": collection.get("asset_type"),
            "schema_version": collection.get("schema_version"),
            "count": len(paths),
            "path_types": [p.get("path_type") for p in paths],
            "paths": paths,
        }

    @staticmethod
    def _relationships(meaning_asset: Dict[str, Any], primitive_collection: Dict[str, Any]) -> Dict[str, Any]:
        relationships = meaning_asset.get("relationships") or {}
        related: Set[str] = set()
        if isinstance(relationships, dict):
            for value in relationships.values():
                if isinstance(value, list):
                    related.update(str(item) for item in value)
                elif isinstance(value, str):
                    related.add(value)
        for primitive in primitive_collection.get("primitives", []):
            if primitive.get("primitive_type") == "related_concepts":
                concepts = primitive.get("content", {}).get("related_concepts", [])
                related.update(str(item) for item in concepts)
        return {
            "source_relationships": relationships,
            "related_concepts": sorted(related),
        }

    @staticmethod
    def _traceability(
        meaning_asset: Dict[str, Any],
        primitive_collection: Dict[str, Any],
        path_collection: Dict[str, Any],
    ) -> UnderstandingAssetTraceability:
        evidence_refs: Set[str] = set()
        for primitive in primitive_collection.get("primitives", []):
            evidence_refs.update(str(ref) for ref in primitive.get("evidence_refs", []))
        for ref in meaning_asset.get("evidence_refs", []):
            evidence_refs.add(str(ref))
        return UnderstandingAssetTraceability(
            meaning_asset_id=meaning_asset.get("asset_id") or meaning_asset.get("meaning_asset_id") or "unknown",
            learning_primitive_collection_id=primitive_collection.get("asset_id", "unknown"),
            learning_path_collection_id=path_collection.get("asset_id", "unknown"),
            source_evidence_refs=sorted(evidence_refs),
            source_asset_types={
                "meaning_asset": meaning_asset.get("asset_type", "unknown"),
                "learning_primitive_collection": primitive_collection.get("asset_type", "unknown"),
                "learning_path_collection": path_collection.get("asset_type", "unknown"),
            },
        )

    @staticmethod
    def _build_learning_outcomes(primitives: Iterable[Dict[str, Any]], paths: Iterable[Dict[str, Any]]) -> List[str]:
        outcomes: List[str] = []
        seen = set()
        for primitive in primitives:
            objective = primitive.get("learning_objective")
            if objective and objective not in seen:
                outcomes.append(objective)
                seen.add(objective)
        for path in paths:
            for criterion in path.get("success_criteria", []):
                if criterion and criterion not in seen:
                    outcomes.append(criterion)
                    seen.add(criterion)
        return outcomes
