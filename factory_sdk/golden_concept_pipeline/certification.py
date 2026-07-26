from __future__ import annotations

from .execution_models import ManufacturingState
from .pipeline_models import (
    DependencyGraph,
    DispatchPlan,
    GoldenConceptCertification,
    GoldenConceptPackage,
    ManufacturingQueue,
)


class GoldenConceptCertifier:
    """Certifies both GCMP planning quality and execution completeness."""

    REQUIRED_ASSET_TYPES = {"knowledge_asset", "understanding_gap"}

    def certify(
        self,
        *,
        concept_id: str,
        queue: ManufacturingQueue,
        graph: DependencyGraph,
        dispatch: DispatchPlan,
        package: GoldenConceptPackage,
        state: ManufacturingState,
    ) -> GoldenConceptCertification:
        asset_types = {task.asset_type for task in queue.tasks}

        planning_checks = {
            "queue_created": {
                "pass": len(queue.tasks) > 0,
                "detail": f"{len(queue.tasks)} tasks planned",
            },
            "dependencies_resolved": {
                "pass": len(graph.unresolved_dependencies) == 0,
                "detail": f"{len(graph.edges)} dependency edges",
            },
            "dispatch_plan_created": {
                "pass": len(dispatch.items) == len(queue.tasks),
                "detail": f"{len(dispatch.items)} dispatch items",
            },
            "package_created": {
                "pass": package.task_count == len(queue.tasks),
                "detail": package.package_id,
            },
            "minimum_foundation_present": {
                "pass": self.REQUIRED_ASSET_TYPES.issubset(asset_types),
                "detail": (
                    f"required={sorted(self.REQUIRED_ASSET_TYPES)} "
                    f"present={sorted(asset_types)}"
                ),
            },
        }

        pass_count = state.summary.get("PASS", 0)
        skipped_count = state.summary.get("SKIPPED", 0)
        waiting_count = state.summary.get("WAITING", 0)
        fail_count = state.summary.get("FAIL", 0)

        execution_checks = {
            "execution_results_recorded": {
                "pass": len(state.items) == len(queue.tasks),
                "detail": (
                    f"state_items={len(state.items)} "
                    f"planned_tasks={len(queue.tasks)}"
                ),
            },
            "no_execution_failures": {
                "pass": fail_count == 0,
                "detail": f"FAIL={fail_count}",
            },
            "all_planned_tasks_completed": {
                "pass": (
                    pass_count == len(queue.tasks)
                    and skipped_count == 0
                    and waiting_count == 0
                    and fail_count == 0
                ),
                "detail": (
                    f"PASS={pass_count}, SKIPPED={skipped_count}, "
                    f"WAITING={waiting_count}, FAIL={fail_count}"
                ),
            },
        }

        planning_status = (
            "PASS"
            if all(check["pass"] for check in planning_checks.values())
            else "FAIL"
        )

        execution_status = self._execution_status(
            pass_count=pass_count,
            skipped_count=skipped_count,
            waiting_count=waiting_count,
            fail_count=fail_count,
            task_count=len(queue.tasks),
        )

        return GoldenConceptCertification.create(
            concept_id=concept_id,
            planning_status=planning_status,
            execution_status=execution_status,
            checks={
                "planning": planning_checks,
                "execution": execution_checks,
            },
            execution_summary=state.summary,
        )

    @staticmethod
    def _execution_status(
        *,
        pass_count: int,
        skipped_count: int,
        waiting_count: int,
        fail_count: int,
        task_count: int,
    ) -> str:
        if fail_count > 0:
            return "FAILED"

        if task_count == 0 or pass_count == 0:
            return "NOT_STARTED"

        if (
            pass_count == task_count
            and skipped_count == 0
            and waiting_count == 0
        ):
            return "COMPLETE"

        return "PARTIAL"