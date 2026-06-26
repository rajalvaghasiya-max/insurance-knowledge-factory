"""
PolicyScna Factory SDK v1.2 — Factory Lineage

Lineage records how a manufactured asset was created from input assets and
source evidence. This implements the principle:

    Evidence is permanent. Understanding is versioned. Wisdom evolves.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class LineageReference:
    reference_type: str
    reference_id: str
    asset_type: Optional[str] = None
    path: Optional[str] = None
    role: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FactoryLineage:
    input_assets: List[LineageReference] = field(default_factory=list)
    source_evidence: List[LineageReference] = field(default_factory=list)
    derived_from: List[LineageReference] = field(default_factory=list)
    transformation_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_paths(
        cls,
        *,
        input_paths: Optional[List[str]] = None,
        output_source_evidence_ids: Optional[List[str]] = None,
    ) -> "FactoryLineage":
        input_assets = [
            LineageReference(reference_type="input_asset", reference_id=path, path=path)
            for path in (input_paths or [])
        ]
        source_evidence = [
            LineageReference(reference_type="source_evidence", reference_id=eid)
            for eid in (output_source_evidence_ids or [])
        ]
        return cls(input_assets=input_assets, source_evidence=source_evidence)
