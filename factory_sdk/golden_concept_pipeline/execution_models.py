from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .pipeline_models import ManufacturingTask, stable_hash, utc_now


@dataclass(frozen=True)
class ManufacturingContext:
    """Runtime context passed from GCMP to a production cell.

    GCMP coordinates; production cells manufacture.  This object keeps that
    boundary clean by giving every cell the same input shape.
    """

    concept_id: str
    task: ManufacturingTask
    working_directory: str
    distillation_reports_dir: str
    report_paths_by_id: Dict[str, str]
    completed_assets: Dict[str, List[str]] = field(default_factory=dict)

    def primary_report_path(self) -> Optional[str]:
        for distillation_id in self.task.source_distillation_ids:
            path = self.report_paths_by_id.get(distillation_id)
            if path:
                return path
        return None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["task"] = self.task.to_dict()
        return data


@dataclass(frozen=True)
class ProductionResult:
    task_id: str
    asset_type: str
    production_cell: str
    status: str
    output_paths: Dict[str, str] = field(default_factory=dict)
    message: str = ""
    created_at: str = field(default_factory=utc_now)

    @staticmethod
    def pass_result(*, task: ManufacturingTask, production_cell: str, output_paths: Dict[str, str], message: str = "") -> "ProductionResult":
        return ProductionResult(
            task_id=task.task_id,
            asset_type=task.asset_type,
            production_cell=production_cell,
            status="PASS",
            output_paths=output_paths,
            message=message,
        )

    @staticmethod
    def skipped(*, task: ManufacturingTask, production_cell: str, message: str) -> "ProductionResult":
        return ProductionResult(
            task_id=task.task_id,
            asset_type=task.asset_type,
            production_cell=production_cell,
            status="SKIPPED",
            message=message,
        )

    @staticmethod
    def fail_result(*, task: ManufacturingTask, production_cell: str, message: str) -> "ProductionResult":
        return ProductionResult(
            task_id=task.task_id,
            asset_type=task.asset_type,
            production_cell=production_cell,
            status="FAIL",
            message=message,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ManufacturingStateItem:
    asset_type: str
    task_id: str
    production_cell: str
    status: str
    dependencies: List[str]
    output_paths: Dict[str, str] = field(default_factory=dict)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ManufacturingState:
    state_id: str
    concept_id: str
    items: List[ManufacturingStateItem]
    summary: Dict[str, int]
    created_at: str

    @staticmethod
    def create(concept_id: str, items: List[ManufacturingStateItem]) -> "ManufacturingState":
        summary: Dict[str, int] = {}
        for item in items:
            summary[item.status] = summary.get(item.status, 0) + 1
        payload = {"concept_id": concept_id, "items": [i.to_dict() for i in items], "summary": summary}
        return ManufacturingState(
            state_id=f"gms_{stable_hash(payload)}",
            concept_id=concept_id,
            items=items,
            summary=summary,
            created_at=utc_now(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutionLog:
    execution_id: str
    concept_id: str
    results: List[ProductionResult]
    created_at: str

    @staticmethod
    def create(concept_id: str, results: List[ProductionResult]) -> "ExecutionLog":
        payload = {"concept_id": concept_id, "results": [r.to_dict() for r in results]}
        return ExecutionLog(
            execution_id=f"gex_{stable_hash(payload)}",
            concept_id=concept_id,
            results=results,
            created_at=utc_now(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
