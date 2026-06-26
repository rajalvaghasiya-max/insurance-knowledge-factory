from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set

from .execution_models import ExecutionLog, ManufacturingContext, ProductionResult
from .pipeline_models import ManufacturingQueue, SourceDistillationReport
from .production_cell_registry import ProductionCellRegistry


class ExecutionDispatcher:
    """Executes registered production cells in dependency-safe queue order."""

    def __init__(self, registry: ProductionCellRegistry) -> None:
        self.registry = registry

    def execute(
        self,
        *,
        queue: ManufacturingQueue,
        reports: List[SourceDistillationReport],
        working_directory: str | Path,
        distillation_reports_dir: str | Path,
    ) -> ExecutionLog:
        completed_assets: Dict[str, List[str]] = {}
        completed_asset_types: Set[str] = set()
        results: List[ProductionResult] = []
        report_paths_by_id = {
            report.distillation_id: str(report.source_path)
            for report in reports
            if report.source_path
        }

        for task in queue.tasks:
            missing_dependencies = [dep for dep in task.dependencies if dep not in completed_asset_types]
            if missing_dependencies:
                results.append(
                    ProductionResult.skipped(
                        task=task,
                        production_cell="dependency_gate",
                        message=f"Waiting for dependencies: {', '.join(missing_dependencies)}",
                    )
                )
                continue

            cell = self.registry.get(task.asset_type)
            if cell is None:
                results.append(
                    ProductionResult.skipped(
                        task=task,
                        production_cell="unregistered_cell",
                        message=f"No executable production cell registered for {task.asset_type}.",
                    )
                )
                continue

            context = ManufacturingContext(
                concept_id=queue.concept_id,
                task=task,
                working_directory=str(working_directory),
                distillation_reports_dir=str(distillation_reports_dir),
                report_paths_by_id=report_paths_by_id,
                completed_assets=completed_assets,
            )
            result = cell.run(context)
            results.append(result)
            if result.status == "PASS":
                completed_asset_types.add(task.asset_type)
                completed_assets.setdefault(task.asset_type, []).extend(result.output_paths.values())

        return ExecutionLog.create(queue.concept_id, results)
