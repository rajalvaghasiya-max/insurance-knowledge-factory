from __future__ import annotations

from typing import Dict, List, Tuple

from .pipeline_models import DependencyGraph, ManufacturingQueue, ManufacturingTask


DEPENDENCY_RULES: Dict[str, List[str]] = {
    "understanding_gap": ["knowledge_asset"],
    "mental_model_asset": ["knowledge_asset", "understanding_gap"],
    "verification_question": ["mental_model_asset"],
    "financial_simulation": ["knowledge_asset", "understanding_gap"],
    "golden_rule": ["understanding_gap"],
    "claims_intelligence": ["financial_simulation"],
    "decision_case": ["mental_model_asset", "financial_simulation"],
    "decision_intelligence_case": ["mental_model_asset", "financial_simulation"],
    "behaviour_goal": ["mental_model_asset"],
    "advisor_intelligence_asset": ["understanding_gap"],
    "conversation_blueprint": ["advisor_intelligence_asset", "golden_rule"],
}

DEPENDENCY_DEPARTMENTS: Dict[str, str] = {
    "knowledge_asset": "Department IV",
    "understanding_gap": "Department V",
    "mental_model_asset": "MMTS",
    "financial_simulation": "Department V",
    "golden_rule": "Department V",
}


class DependencyResolver:
    """Adds prerequisite manufacturing tasks and produces a dependency graph."""

    def resolve(self, queue: ManufacturingQueue) -> Tuple[ManufacturingQueue, DependencyGraph]:
        tasks_by_asset = {task.asset_type: task for task in queue.tasks}
        added: List[ManufacturingTask] = []
        all_tasks = list(queue.tasks)

        changed = True
        while changed:
            changed = False
            for task in list(all_tasks):
                for dependency in DEPENDENCY_RULES.get(task.asset_type, []):
                    if dependency not in tasks_by_asset:
                        dep_task = ManufacturingTask.create(
                            concept_id=queue.concept_id,
                            asset_type=dependency,
                            target_department=DEPENDENCY_DEPARTMENTS.get(dependency, "unassigned"),
                            priority="high",
                            reason=f"Required dependency for {task.asset_type}",
                            source_distillation_ids=task.source_distillation_ids,
                            source_observation_ids=task.source_observation_ids,
                            is_dependency_task=True,
                        )
                        tasks_by_asset[dependency] = dep_task
                        added.append(dep_task)
                        all_tasks.append(dep_task)
                        changed = True

        updated_tasks: List[ManufacturingTask] = []
        for task in all_tasks:
            deps = DEPENDENCY_RULES.get(task.asset_type, [])
            updated_tasks.append(
                ManufacturingTask.create(
                    concept_id=task.concept_id,
                    asset_type=task.asset_type,
                    target_department=task.target_department,
                    priority=task.priority,
                    reason=task.reason,
                    source_distillation_ids=task.source_distillation_ids,
                    source_observation_ids=task.source_observation_ids,
                    dependencies=deps,
                    is_dependency_task=task.is_dependency_task,
                )
            )

        order = self._topological_sort(updated_tasks)
        ordered_tasks = [next(t for t in updated_tasks if t.asset_type == asset_type) for asset_type in order]
        resolved_queue = ManufacturingQueue.create(queue.concept_id, queue.source_reports, ordered_tasks)

        nodes = [task.asset_type for task in resolved_queue.tasks]
        edges = [
            {"from": dependency, "to": task.asset_type}
            for task in resolved_queue.tasks
            for dependency in task.dependencies
        ]
        graph = DependencyGraph.create(queue.concept_id, nodes, edges, unresolved=[])
        return resolved_queue, graph

    def _topological_sort(self, tasks: List[ManufacturingTask]) -> List[str]:
        assets = {task.asset_type for task in tasks}
        visited: set[str] = set()
        visiting: set[str] = set()
        result: List[str] = []

        def visit(asset: str) -> None:
            if asset in visited:
                return
            if asset in visiting:
                return
            visiting.add(asset)
            for dep in DEPENDENCY_RULES.get(asset, []):
                if dep in assets:
                    visit(dep)
            visiting.remove(asset)
            visited.add(asset)
            result.append(asset)

        for asset in sorted(assets):
            visit(asset)
        return result
