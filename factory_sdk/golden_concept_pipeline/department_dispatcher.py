from __future__ import annotations

from typing import Dict

from .pipeline_models import DispatchItem, DispatchPlan, ManufacturingQueue


PRODUCTION_CELL_MAP: Dict[str, str] = {
    "Department IV": "knowledge_manufacturing_cell",
    "Department V": "understanding_manufacturing_cell",
    "MMTS": "mental_model_transformation_cell",
    "Advisor Intelligence": "advisor_intelligence_cell",
    "Decision Intelligence": "decision_intelligence_cell",
    "Claims Intelligence": "claims_intelligence_cell",
}


class DepartmentDispatcher:
    """Creates a dispatch plan. v1.0 does not execute downstream departments."""

    def dispatch(self, queue: ManufacturingQueue) -> DispatchPlan:
        items = []
        for task in queue.tasks:
            cell = PRODUCTION_CELL_MAP.get(task.target_department, "manual_review_cell")
            items.append(
                DispatchItem(
                    task_id=task.task_id,
                    asset_type=task.asset_type,
                    target_department=task.target_department,
                    production_cell=cell,
                    dispatch_mode="planned_not_executed",
                    status="ready_for_downstream_manufacturing",
                )
            )
        return DispatchPlan.create(queue.concept_id, items)
