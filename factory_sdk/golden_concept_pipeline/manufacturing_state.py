from __future__ import annotations

from typing import Dict, List

from .execution_models import ManufacturingState, ManufacturingStateItem, ProductionResult
from .pipeline_models import DispatchPlan, ManufacturingQueue


class ManufacturingStateManager:
    def build_state(
        self,
        *,
        queue: ManufacturingQueue,
        dispatch: DispatchPlan,
        results: List[ProductionResult],
    ) -> ManufacturingState:
        result_by_task = {result.task_id: result for result in results}
        dispatch_by_task = {item.task_id: item for item in dispatch.items}
        items: List[ManufacturingStateItem] = []
        for task in queue.tasks:
            dispatch_item = dispatch_by_task.get(task.task_id)
            result = result_by_task.get(task.task_id)
            if result:
                status = result.status
                production_cell = result.production_cell
                outputs = result.output_paths
                message = result.message
            else:
                status = "WAITING"
                production_cell = dispatch_item.production_cell if dispatch_item else "unknown"
                outputs = {}
                message = "No execution result recorded."
            items.append(
                ManufacturingStateItem(
                    asset_type=task.asset_type,
                    task_id=task.task_id,
                    production_cell=production_cell,
                    status=status,
                    dependencies=task.dependencies,
                    output_paths=outputs,
                    message=message,
                )
            )
        return ManufacturingState.create(queue.concept_id, items)
