"""
PolicyScna Factory SDK v1.2 — Factory Report

Standard report object for every production line.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .factory_metadata import utc_now_iso


@dataclass(frozen=True)
class FactoryReport:
    report_id: str
    report_type: str
    engine: str
    department: str
    production_line: str
    input_asset_count: int
    output_asset_count: int
    quality_score: float
    validation_status: str
    department_boundary: str
    next_stage: Optional[str] = None
    statistics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    report_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "report_type": self.report_type,
            "report_version": self.report_version,
            "created_at": self.created_at,
            "engine": self.engine,
            "department": self.department,
            "production_line": self.production_line,
            "input_asset_count": self.input_asset_count,
            "output_asset_count": self.output_asset_count,
            "quality_score": self.quality_score,
            "validation_status": self.validation_status,
            "warnings": self.warnings,
            "errors": self.errors,
            "department_boundary": self.department_boundary,
            "next_stage": self.next_stage,
            "statistics": self.statistics,
        }
