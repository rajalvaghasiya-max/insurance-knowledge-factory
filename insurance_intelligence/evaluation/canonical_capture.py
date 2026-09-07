"""Capture the current canonical guarded response execution for deterministic evaluation.

This module adapts already-produced orchestration stage results and typed runtime
objects into the immutable MO-021 evaluation capture model. It never executes or
re-executes an insurance-intelligence stage.
"""
from __future__ import annotations

from typing import Mapping, Sequence

from insurance_intelligence.contracts.full_cycle import OrchestrationRequest, StageResult
from insurance_intelligence.evaluation.runner import FixtureExecution, PipelineRun, StageExecution
from insurance_intelligence.orchestration.execution_state import RuntimeStageObjectStore


class CanonicalEvaluationCaptureError(ValueError):
    """Raised when a canonical execution prefix cannot be captured safely."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CanonicalEvaluationCaptureError(f"{label} must be non-empty text")
    return value.strip()


def _trace_events(value: object) -> tuple[str, ...]:
    candidates = (
        "response_trace",
        "explanation_trace",
        "decision_trace",
        "reasoning_trace",
        "resolution_trace",
        "planning_trace",
        "context_trace",
        "intent_trace",
        "trace",
    )
    trace: object | None = None
    for name in candidates:
        candidate = getattr(value, name, None)
        if candidate is not None:
            trace = candidate
            break
    if trace is None and isinstance(value, Mapping):
        for name in candidates:
            if name in value:
                trace = value[name]
                break
    if trace is None:
        return ()
    events: list[str] = []
    try:
        items = tuple(trace)  # type: ignore[arg-type]
    except TypeError:
        return ()
    for item in items:
        event = getattr(item, "event_type", None)
        if event is None and isinstance(item, Mapping):
            event = item.get("event_type")
        if isinstance(event, str) and event.strip():
            events.append(event.strip())
    return tuple(events)


def capture_canonical_execution(
    *,
    request: OrchestrationRequest,
    stage_results: Sequence[StageResult],
    store: RuntimeStageObjectStore,
    released_response_id: str,
    scenario_id: str,
    scenario_version: str,
    fixture_id: str,
    run_number: int = 1,
) -> FixtureExecution:
    """Convert an already executed guarded response prefix into evaluation capture data.

    The captured orchestration prefix must end at ``LLM_RENDERING``. A final
    evaluation-only ``RELEASED_RESPONSE_CAPTURE`` record is appended so the existing
    assertion engine can score response status, audience and format without rewriting
    the true ``LLM_RENDERING`` result (for example ``NOT_REQUIRED``).
    """
    if not isinstance(request, OrchestrationRequest):
        raise CanonicalEvaluationCaptureError("request must be OrchestrationRequest")
    if not isinstance(store, RuntimeStageObjectStore):
        raise CanonicalEvaluationCaptureError("store must be RuntimeStageObjectStore")
    if store.execution_id != request.execution_id:
        raise CanonicalEvaluationCaptureError("runtime store execution identity mismatch")
    if isinstance(run_number, bool) or not isinstance(run_number, int) or run_number < 1:
        raise CanonicalEvaluationCaptureError("run_number must be an integer of at least 1")

    results = tuple(stage_results)
    if not results:
        raise CanonicalEvaluationCaptureError("stage_results must contain a canonical execution prefix")
    expected = request.requested_stage_order[: len(results)]
    actual = tuple(result.stage for result in results)
    if actual != expected:
        raise CanonicalEvaluationCaptureError("stage_results must match the governed requested-stage prefix")
    for sequence, result in enumerate(results, start=1):
        if result.execution_id != request.execution_id:
            raise CanonicalEvaluationCaptureError("stage result execution identity mismatch")
        if result.sequence != sequence:
            raise CanonicalEvaluationCaptureError("stage result sequence must be contiguous from 1")
    if results[-1].stage != "LLM_RENDERING":
        raise CanonicalEvaluationCaptureError("canonical final-evaluation capture must end at LLM_RENDERING")
    failed = tuple(result for result in results if result.status in {"FAILED", "BLOCKED"})
    if failed:
        first = failed[0]
        raise CanonicalEvaluationCaptureError(
            f"cannot evaluate an unsuccessful canonical prefix: {first.stage}={first.status}"
        )

    released_id = _text(released_response_id, "released_response_id")
    released_response = store.get(released_id)

    executions: list[StageExecution] = []
    for result in results:
        output_ids = tuple(item.output_id for item in result.outputs)
        if output_ids:
            values = store.resolve(output_ids)
            captured_output: object = values[0] if len(values) == 1 else values
        else:
            captured_output = {
                "stage": result.stage,
                "status": result.status,
                "input_ids": result.input_ids,
            }
        executions.append(
            StageExecution(
                stage=result.stage,
                sequence=result.sequence,
                status=result.status,
                output=captured_output,
                trace_events=_trace_events(captured_output),
                execution_id=f"canonical-capture:{request.execution_id}:{result.sequence}:{result.stage.lower()}",
            )
        )

    response_status = getattr(released_response, "response_status", None)
    if not isinstance(response_status, str) or not response_status.strip():
        raise CanonicalEvaluationCaptureError("released response must expose a response_status")
    executions.append(
        StageExecution(
            stage="RELEASED_RESPONSE_CAPTURE",
            sequence=len(executions) + 1,
            status=response_status.strip(),
            output=released_response,
            trace_events=_trace_events(released_response),
            execution_id=f"canonical-capture:{request.execution_id}:released-response",
        )
    )

    selected_scenario = _text(scenario_id, "scenario_id")
    selected_version = _text(scenario_version, "scenario_version")
    selected_fixture = _text(fixture_id, "fixture_id")
    run = PipelineRun(
        run_id=f"canonical-run:{request.execution_id}:{run_number}",
        fixture_id=selected_fixture,
        scenario_id=selected_scenario,
        scenario_version=selected_version,
        request_id=request.execution_id,
        run_number=run_number,
        stage_executions=tuple(executions),
        completed=True,
        failed_stage=None,
        failure_reason=None,
    )
    return FixtureExecution(
        execution_id=f"canonical-evaluation-capture:{request.execution_id}:{selected_scenario}",
        fixture_id=selected_fixture,
        scenario_id=selected_scenario,
        scenario_version=selected_version,
        runs=(run,),
    )


__all__ = ["CanonicalEvaluationCaptureError", "capture_canonical_execution"]
