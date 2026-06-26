"""
PolicyScna Department V — Understanding Asset Models v1.0

An Understanding Asset is the certified package that assembles a Meaning Asset,
Learning Primitive Collection, and Learning Path Collection for one concept.
It does not create new educational content, personalize, recommend, or converse.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class UnderstandingAssetTraceability:
    meaning_asset_id: str
    learning_primitive_collection_id: str
    learning_path_collection_id: str
    source_evidence_refs: List[str] = field(default_factory=list)
    source_asset_types: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UnderstandingAssetFactorySignature:
    factory: str
    department: str
    production_line: str
    engine_version: str
    rules_version: str
    schema_version: str
    factory_version: str
    sdk_version: str
    deterministic: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UnderstandingAsset:
    asset_id: str
    asset_type: str
    schema_version: str
    asset_version: str
    department_boundary: str
    concept_id: str
    concept_name: str
    meaning: Dict[str, Any]
    learning_primitives: Dict[str, Any]
    learning_paths: Dict[str, Any]
    learning_outcomes: List[str]
    relationships: Dict[str, Any]
    traceability: UnderstandingAssetTraceability
    factory_signature: UnderstandingAssetFactorySignature
    notes: List[str] = field(default_factory=list)
    status: str = "certified_candidate"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["traceability"] = self.traceability.to_dict()
        data["factory_signature"] = self.factory_signature.to_dict()
        return data
