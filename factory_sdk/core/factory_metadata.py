"""
PolicyScna Factory SDK v1.2 — Factory Metadata

Shared metadata model for every manufactured asset, report, certification,
and event produced by the Factory.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class FactoryVersionSet:
    factory_version: str = "1.0"
    department_version: str = "1.0"
    engine_version: str = "1.0"
    rules_version: str = "1.0"
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FactoryMetadata:
    manufactured_by: str
    manufactured_at: str
    department: str
    production_line: str
    asset_type: str
    versions: FactoryVersionSet
    deterministic: bool = True
    department_boundary: str = ""
    input_assets: List[str] = field(default_factory=list)
    source_evidence: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(
        cls,
        *,
        manufactured_by: str,
        department: str,
        production_line: str,
        asset_type: str,
        versions: FactoryVersionSet,
        deterministic: bool = True,
        department_boundary: str = "",
        input_assets: Optional[List[str]] = None,
        source_evidence: Optional[List[str]] = None,
        notes: Optional[List[str]] = None,
    ) -> "FactoryMetadata":
        return cls(
            manufactured_by=manufactured_by,
            manufactured_at=utc_now_iso(),
            department=department,
            production_line=production_line,
            asset_type=asset_type,
            versions=versions,
            deterministic=deterministic,
            department_boundary=department_boundary,
            input_assets=input_assets or [],
            source_evidence=source_evidence or [],
            notes=notes or [],
        )
