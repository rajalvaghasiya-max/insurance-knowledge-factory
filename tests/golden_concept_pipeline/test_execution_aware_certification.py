from factory_sdk.golden_concept_pipeline.execution_models import (
    ManufacturingState,
    ManufacturingStateItem,
)
from factory_sdk.golden_concept_pipeline.pipeline_models import (
    DependencyGraph,
    DispatchItem,
    DispatchPlan,
    GoldenConceptPackage,
    ManufacturingQueue,
    ManufacturingTask,
)
from factory_sdk.golden_concept_pipeline.certification import GoldenConceptCertifier


def build_queue():
    knowledge_task = ManufacturingTask.create(
        concept_id="waiting_period",
        asset_type="knowledge_asset",
        target_department="Department IV",
        priority="high",
        reason="Foundation",
        source_distillation_ids=["kdr_test"],
        source_observation_ids=["OBS-001"],
        is_dependency_task=True,
    )

    understanding_task = ManufacturingTask.create(
        concept_id="waiting_period",
        asset_type="understanding_gap",
        target_department="Department V",
        priority="high",
        reason="Understanding needed",
        source_distillation_ids=["kdr_test"],
        source_observation_ids=["OBS-001"],
        dependencies=["knowledge_asset"],
    )

    mental_model_task = ManufacturingTask.create(
        concept_id="waiting_period",
        asset_type="mental_model_asset",
        target_department="MMTS",
        priority="high",
        reason="Mental model needed",
        source_distillation_ids=["kdr_test"],
        source_observation_ids=["OBS-001"],
        dependencies=["knowledge_asset", "understanding_gap"],
    )

    return ManufacturingQueue.create(
        concept_id="waiting_period",
        source_reports=["kdr_test"],
        tasks=[knowledge_task, understanding_task, mental_model_task],
    )


def build_dispatch(queue):
    items = [
        DispatchItem(
            task_id=task.task_id,
            asset_type=task.asset_type,
            target_department=task.target_department,
            production_cell="test_cell",
            dispatch_mode="planned_not_executed",
            status="ready_for_downstream_manufacturing",
        )
        for task in queue.tasks
    ]

    return DispatchPlan.create("waiting_period", items)


def build_state(queue):
    items = [
        ManufacturingStateItem(
            asset_type=queue.tasks[0].asset_type,
            task_id=queue.tasks[0].task_id,
            production_cell="foundation_passthrough_cell",
            status="PASS",
            dependencies=[],
        ),
        ManufacturingStateItem(
            asset_type=queue.tasks[1].asset_type,
            task_id=queue.tasks[1].task_id,
            production_cell="foundation_passthrough_cell",
            status="PASS",
            dependencies=["knowledge_asset"],
        ),
        ManufacturingStateItem(
            asset_type=queue.tasks[2].asset_type,
            task_id=queue.tasks[2].task_id,
            production_cell="mental_model_transformation_cell",
            status="SKIPPED",
            dependencies=["knowledge_asset", "understanding_gap"],
            message="Concept not supported.",
        ),
    ]

    return ManufacturingState.create("waiting_period", items)


def test_partial_execution_returns_pass_with_gaps():
    queue = build_queue()
    dispatch = build_dispatch(queue)
    state = build_state(queue)

    graph = DependencyGraph.create(
        concept_id="waiting_period",
        nodes=[task.asset_type for task in queue.tasks],
        edges=[],
        unresolved=[],
    )

    package = GoldenConceptPackage.create(
        concept_id="waiting_period",
        source_reports=[],
        queue=queue,
    )

    certification = GoldenConceptCertifier().certify(
        concept_id="waiting_period",
        queue=queue,
        graph=graph,
        dispatch=dispatch,
        package=package,
        state=state,
    )

    assert certification.planning_status == "PASS"
    assert certification.execution_status == "PARTIAL"
    assert certification.status == "PASS_WITH_GAPS"
    assert certification.execution_summary["SKIPPED"] == 1