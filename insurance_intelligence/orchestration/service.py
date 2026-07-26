"""Executable governed orchestration services for MO-023E."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from insurance_intelligence.contracts.full_cycle import (
    INTELLIGENCE_RESPONSE_STAGE_ORDER,
    KNOWLEDGE_BUILD_STAGE_ORDER,
    FullCycleResult,
    OrchestrationRequest,
    StageResult,
    build_full_cycle_result,
    build_trace_event,
)
from insurance_intelligence.orchestration.execution_state import ExecutionState, build_execution_state
from insurance_intelligence.orchestration.intelligence_adapters import (
    IntelligenceStageAdapter,
    execute_intelligence_adapter_chain,
)
from insurance_intelligence.orchestration.knowledge_adapters import (
    KnowledgeStageAdapter,
    execute_knowledge_adapter_chain,
)


class OrchestrationServiceError(ValueError):
    """Raised when executable orchestration is configured unsafely."""


@dataclass(frozen=True)
class OrchestrationExecution:
    request: OrchestrationRequest
    result: FullCycleResult
    state: ExecutionState


def _trace_for_results(request: OrchestrationRequest, results: Sequence[StageResult]):
    events = [
        build_trace_event(
            event_id=f"trace:{request.execution_id}:1:execution-started",
            execution_id=request.execution_id,
            sequence=1,
            event_type="EXECUTION_STARTED",
            message=f"{request.mode} execution started.",
        )
    ]
    for result in results:
        if result.status in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"}:
            event_type = "STAGE_COMPLETED"
            refs = tuple(output.output_id for output in result.outputs)
        elif result.status in {"SKIPPED", "NOT_REQUIRED"}:
            event_type = "STAGE_SKIPPED"
            refs = ()
        elif result.status == "BLOCKED":
            event_type = "STAGE_BLOCKED"
            refs = (result.failure.failure_id,) if result.failure else ()
        elif result.status == "FAILED":
            event_type = "STAGE_FAILED"
            refs = (result.failure.failure_id,) if result.failure else ()
        else:
            raise OrchestrationServiceError("service accepts only terminal stage results")
        sequence = len(events) + 1
        events.append(
            build_trace_event(
                event_id=f"trace:{request.execution_id}:{sequence}:{result.stage.lower()}",
                execution_id=request.execution_id,
                sequence=sequence,
                event_type=event_type,
                stage=result.stage,
                reference_ids=refs,
                message=f"{result.stage} finished with status {result.status}.",
            )
        )
    sequence = len(events) + 1
    events.append(
        build_trace_event(
            event_id=f"trace:{request.execution_id}:{sequence}:execution-completed",
            execution_id=request.execution_id,
            sequence=sequence,
            event_type="EXECUTION_COMPLETED",
            message=f"{request.mode} execution completed.",
        )
    )
    return tuple(events)


def _cycle_status(results: Sequence[StageResult]) -> str:
    if any(result.status == "FAILED" for result in results):
        return "FAILED"
    if any(result.status == "BLOCKED" for result in results):
        return "BLOCKED"
    if any(result.status == "SUCCEEDED_WITH_LIMITATIONS" for result in results):
        return "SUCCEEDED_WITH_LIMITATIONS"
    return "SUCCEEDED"


def _limitations(results: Sequence[StageResult]) -> tuple[str, ...]:
    values: list[str] = []
    for result in results:
        for limitation in result.limitations:
            if limitation not in values:
                values.append(limitation)
    return tuple(values)


def _finalise(
    *,
    request: OrchestrationRequest,
    stage_results: Sequence[StageResult],
    knowledge_snapshot_id: str | None,
    deterministic_response_id: str | None = None,
    released_response_id: str | None = None,
    evaluation_report_id: str | None = None,
) -> OrchestrationExecution:
    stages = tuple(stage_results)
    trace = _trace_for_results(request, stages)
    status = _cycle_status(stages)
    limits = _limitations(stages)
    result = build_full_cycle_result(
        execution_id=request.execution_id,
        mode=request.mode,
        status=status,
        stage_results=stages,
        trace=trace,
        knowledge_snapshot_id=knowledge_snapshot_id if status in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"} else None,
        deterministic_response_id=deterministic_response_id if status in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"} else None,
        released_response_id=released_response_id if status in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"} else None,
        evaluation_report_id=evaluation_report_id if status in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"} else None,
        limitations=limits,
    )
    state = build_execution_state(request=request, completed_stage_results=stages, trace=trace)
    return OrchestrationExecution(request=request, result=result, state=state)


def run_knowledge_build(*, request: OrchestrationRequest, adapters: Sequence[KnowledgeStageAdapter]) -> OrchestrationExecution:
    if request.mode not in {"KNOWLEDGE_BUILD", "KNOWLEDGE_REFRESH"}:
        raise OrchestrationServiceError("knowledge service requires KNOWLEDGE_BUILD or KNOWLEDGE_REFRESH mode")
    run = execute_knowledge_adapter_chain(request=request, adapters=adapters)
    snapshot = run.output_ids[0] if not run.blocked and run.output_ids else None
    return _finalise(request=request, stage_results=run.stage_results, knowledge_snapshot_id=snapshot)


def run_intelligence_response(
    *, request: OrchestrationRequest, adapters: Sequence[IntelligenceStageAdapter]
) -> OrchestrationExecution:
    if request.mode != "INTELLIGENCE_RESPONSE":
        raise OrchestrationServiceError("response service requires INTELLIGENCE_RESPONSE mode")
    run = execute_intelligence_adapter_chain(request=request, adapters=adapters)
    return _finalise(
        request=request,
        stage_results=run.stage_results,
        knowledge_snapshot_id=run.knowledge_snapshot_id,
        deterministic_response_id=run.deterministic_response_id,
        released_response_id=run.released_response_id,
        evaluation_report_id=run.evaluation_report_id,
    )


def run_full_cycle_certification(
    *,
    request: OrchestrationRequest,
    knowledge_adapters: Sequence[KnowledgeStageAdapter],
    intelligence_adapters: Sequence[IntelligenceStageAdapter],
) -> OrchestrationExecution:
    if request.mode != "FULL_CYCLE_CERTIFICATION":
        raise OrchestrationServiceError("full-cycle service requires FULL_CYCLE_CERTIFICATION mode")
    knowledge = execute_knowledge_adapter_chain(request=request, adapters=knowledge_adapters)
    if knowledge.blocked or not knowledge.output_ids:
        blocked_results = list(knowledge.stage_results)
        prior_inputs: tuple[str, ...] = ()
        for offset, stage in enumerate(INTELLIGENCE_RESPONSE_STAGE_ORDER, start=len(KNOWLEDGE_BUILD_STAGE_ORDER) + 1):
            from insurance_intelligence.contracts.full_cycle import build_failure_record, build_stage_result
            failure = build_failure_record(
                failure_id=f"failure:{request.execution_id}:{stage.lower()}:blocked",
                stage=stage,
                failure_kind="DEPENDENCY_BLOCKED",
                message="Knowledge certification did not complete.",
                blocked_stage_names=INTELLIGENCE_RESPONSE_STAGE_ORDER[offset-len(KNOWLEDGE_BUILD_STAGE_ORDER):],
            )
            blocked_results.append(build_stage_result(
                execution_id=request.execution_id,
                stage=stage,
                sequence=offset,
                status="BLOCKED",
                input_ids=prior_inputs,
                failure=failure,
            ))
        return _finalise(request=request, stage_results=blocked_results, knowledge_snapshot_id=None)

    snapshot = knowledge.output_ids[0]
    intelligence = execute_intelligence_adapter_chain(
        request=request,
        adapters=intelligence_adapters,
        knowledge_snapshot_id=snapshot,
    )
    stages = knowledge.stage_results + intelligence.stage_results
    return _finalise(
        request=request,
        stage_results=stages,
        knowledge_snapshot_id=snapshot,
        deterministic_response_id=intelligence.deterministic_response_id,
        released_response_id=intelligence.released_response_id,
        evaluation_report_id=intelligence.evaluation_report_id,
    )
