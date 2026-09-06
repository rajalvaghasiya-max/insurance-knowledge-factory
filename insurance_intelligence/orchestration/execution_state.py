"""Unified orchestration execution state and safe recovery rules (MO-023D)."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Mapping, Sequence, TypeVar

from insurance_intelligence.contracts.full_cycle import (
    MODE_STAGE_ORDER,
    ExecutionTraceEvent,
    OrchestrationRequest,
    StageResult,
)


class ExecutionStateError(ValueError):
    """Raised when persisted orchestration state is invalid or unsafe to resume."""


TERMINAL_STAGE_STATUSES = frozenset({"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS", "SKIPPED", "NOT_REQUIRED", "BLOCKED", "FAILED"})
VALIDATED_STAGE_STATUSES = frozenset({"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS", "SKIPPED", "NOT_REQUIRED"})
RESUMABLE_FAILURE_KINDS = frozenset({"STAGE_ERROR", "MISSING_OUTPUT", "STALE_KNOWLEDGE"})
NON_RESUMABLE_FAILURE_KINDS = frozenset({"INVALID_INPUT", "IDENTITY_MISMATCH", "UNCERTIFIED_KNOWLEDGE", "PUBLICATION_BLOCKED", "EVALUATION_FAILED"})


@dataclass(frozen=True)
class StageCheckpoint:
    checkpoint_id: str
    execution_id: str
    stage: str
    sequence: int
    status: str
    input_ids: tuple[str, ...]
    output_ids: tuple[str, ...]
    content_digests: tuple[str, ...]
    trace_event_ids: tuple[str, ...]
    state_digest: str


@dataclass(frozen=True)
class ExecutionState:
    execution_id: str
    mode: str
    requested_stage_order: tuple[str, ...]
    completed_stage_results: tuple[StageResult, ...]
    trace: tuple[ExecutionTraceEvent, ...]
    checkpoints: tuple[StageCheckpoint, ...]
    last_validated_sequence: int
    next_stage: str | None
    resumable: bool
    terminal: bool
    state_id: str


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExecutionStateError(f"{label} must be a non-empty string")
    return value.strip()


def _digest(value: Mapping[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def build_stage_checkpoint(*, result: StageResult, trace: Sequence[ExecutionTraceEvent]) -> StageCheckpoint:
    if result.status not in VALIDATED_STAGE_STATUSES:
        raise ExecutionStateError("checkpoints may be created only for validated stage results")
    related = tuple(event for event in trace if event.stage == result.stage)
    if not related:
        raise ExecutionStateError("validated stage checkpoint requires at least one stage trace event")
    if any(event.execution_id != result.execution_id for event in related):
        raise ExecutionStateError("checkpoint trace execution identity mismatch")
    output_ids = tuple(output.output_id for output in result.outputs)
    digests = tuple(output.content_digest for output in result.outputs)
    payload = {
        "execution_id": result.execution_id,
        "stage": result.stage,
        "sequence": result.sequence,
        "status": result.status,
        "input_ids": list(result.input_ids),
        "output_ids": list(output_ids),
        "content_digests": list(digests),
        "trace_event_ids": [event.event_id for event in related],
    }
    state_digest = _digest(payload)
    return StageCheckpoint(
        checkpoint_id=f"checkpoint:{result.execution_id}:{result.sequence}:{state_digest[:16]}",
        execution_id=result.execution_id,
        stage=result.stage,
        sequence=result.sequence,
        status=result.status,
        input_ids=result.input_ids,
        output_ids=output_ids,
        content_digests=digests,
        trace_event_ids=tuple(event.event_id for event in related),
        state_digest=state_digest,
    )


def _validate_prefix(request: OrchestrationRequest, results: tuple[StageResult, ...]) -> None:
    expected = request.requested_stage_order
    if len(results) > len(expected):
        raise ExecutionStateError("execution state contains more stages than requested")
    for index, result in enumerate(results, start=1):
        if result.execution_id != request.execution_id:
            raise ExecutionStateError("stage result execution identity mismatch")
        if result.sequence != index or result.stage != expected[index - 1]:
            raise ExecutionStateError("completed stage results must be a contiguous governed prefix")
        if result.status not in TERMINAL_STAGE_STATUSES:
            raise ExecutionStateError("persisted stage results must be terminal")
    failure_positions = [i for i, result in enumerate(results) if result.status in {"FAILED", "BLOCKED"}]
    if failure_positions:
        first = failure_positions[0]
        if any(result.status not in {"BLOCKED"} for result in results[first + 1 :]):
            raise ExecutionStateError("stages after the first failure must be blocked")


def _validate_trace(execution_id: str, trace: tuple[ExecutionTraceEvent, ...]) -> None:
    if any(event.execution_id != execution_id for event in trace):
        raise ExecutionStateError("trace execution identity mismatch")
    if [event.sequence for event in trace] != list(range(1, len(trace) + 1)):
        raise ExecutionStateError("trace sequences must be contiguous from 1")
    if len({event.event_id for event in trace}) != len(trace):
        raise ExecutionStateError("trace event IDs must be unique")


def _failure_resumable(result: StageResult) -> bool:
    if result.failure is None:
        return False
    if result.failure.failure_kind in NON_RESUMABLE_FAILURE_KINDS:
        return False
    return result.failure.retryable or result.failure.failure_kind in RESUMABLE_FAILURE_KINDS


def build_execution_state(
    *,
    request: OrchestrationRequest,
    completed_stage_results: Sequence[StageResult],
    trace: Sequence[ExecutionTraceEvent],
) -> ExecutionState:
    results = tuple(completed_stage_results)
    events = tuple(trace)
    _validate_prefix(request, results)
    _validate_trace(request.execution_id, events)

    checkpoints: list[StageCheckpoint] = []
    for result in results:
        if result.status in VALIDATED_STAGE_STATUSES:
            checkpoints.append(build_stage_checkpoint(result=result, trace=events))
        else:
            break

    last_validated = checkpoints[-1].sequence if checkpoints else 0
    failure = next((result for result in results if result.status == "FAILED"), None)
    blocked = any(result.status == "BLOCKED" for result in results)
    all_complete = len(results) == len(request.requested_stage_order)
    terminal = all_complete and (failure is None) and not blocked
    resumable = bool(failure and _failure_resumable(failure))

    if failure is not None:
        next_stage = failure.stage if resumable else None
    elif blocked:
        next_stage = None
    elif all_complete:
        next_stage = None
    else:
        next_stage = request.requested_stage_order[len(results)]

    payload = {
        "execution_id": request.execution_id,
        "mode": request.mode,
        "stages": [(r.stage, r.status, r.sequence) for r in results],
        "trace": [event.event_id for event in events],
        "checkpoints": [checkpoint.checkpoint_id for checkpoint in checkpoints],
        "last_validated_sequence": last_validated,
        "next_stage": next_stage,
        "resumable": resumable,
        "terminal": terminal,
    }
    state_digest = _digest(payload)
    return ExecutionState(
        execution_id=request.execution_id,
        mode=request.mode,
        requested_stage_order=request.requested_stage_order,
        completed_stage_results=results,
        trace=events,
        checkpoints=tuple(checkpoints),
        last_validated_sequence=last_validated,
        next_stage=next_stage,
        resumable=resumable,
        terminal=terminal,
        state_id=f"execution-state:{request.execution_id}:{state_digest[:20]}",
    )


def validate_resume(*, request: OrchestrationRequest, state: ExecutionState) -> str:
    if state.execution_id != request.execution_id or state.mode != request.mode:
        raise ExecutionStateError("resume request identity or mode mismatch")
    if state.requested_stage_order != request.requested_stage_order:
        raise ExecutionStateError("resume request stage order mismatch")
    if not state.resumable or state.next_stage is None:
        raise ExecutionStateError("execution state is not resumable")
    expected_sequence = state.last_validated_sequence + 1
    expected_stage = request.requested_stage_order[expected_sequence - 1]
    if state.next_stage != expected_stage:
        raise ExecutionStateError("resume must start from the first unvalidated stage")
    return expected_stage


def merge_resumed_execution(
    *,
    request: OrchestrationRequest,
    prior_state: ExecutionState,
    resumed_stage_results: Sequence[StageResult],
    resumed_trace: Sequence[ExecutionTraceEvent],
) -> ExecutionState:
    resume_stage = validate_resume(request=request, state=prior_state)
    retained = prior_state.completed_stage_results[: prior_state.last_validated_sequence]
    new_results = tuple(resumed_stage_results)
    if not new_results or new_results[0].stage != resume_stage:
        raise ExecutionStateError("resumed results must begin at the validated resume stage")
    expected_start = prior_state.last_validated_sequence + 1
    for offset, result in enumerate(new_results):
        expected_sequence = expected_start + offset
        if result.sequence != expected_sequence:
            raise ExecutionStateError("resumed stage sequence is not contiguous")
        if result.stage != request.requested_stage_order[expected_sequence - 1]:
            raise ExecutionStateError("resumed stage order mismatch")

    prior_events = prior_state.trace
    new_events = tuple(resumed_trace)
    if new_events:
        expected_event_sequence = len(prior_events) + 1
        if new_events[0].sequence != expected_event_sequence:
            raise ExecutionStateError("resumed trace must continue from the prior trace")
    merged_trace = prior_events + new_events
    return build_execution_state(
        request=request,
        completed_stage_results=retained + new_results,
        trace=merged_trace,
    )


T = TypeVar("T")


class RuntimeStageObjectStore:
    """Execution-scoped in-memory handoff for validated typed stage outputs.

    The canonical adapter chain persists only output identifiers and digests. Real
    stage capabilities also need their validated typed predecessor objects. This
    store bridges those two representations for one live execution without
    becoming a second semantic authority or a persisted knowledge store.
    """

    def __init__(self, *, execution_id: str) -> None:
        self._execution_id = _text(execution_id, "execution_id")
        self._objects: dict[str, object] = {}

    @property
    def execution_id(self) -> str:
        return self._execution_id

    def put(self, *, output_id: str, value: object) -> str:
        selected_id = _text(output_id, "output_id")
        if value is None:
            raise ExecutionStateError("runtime stage object must not be None")
        if selected_id in self._objects:
            raise ExecutionStateError(f"runtime stage output already registered: {selected_id}")
        self._objects[selected_id] = value
        return selected_id

    def get(self, output_id: str, *, expected_type: type[T] | None = None) -> T | object:
        selected_id = _text(output_id, "output_id")
        try:
            value = self._objects[selected_id]
        except KeyError as exc:
            raise ExecutionStateError(f"runtime stage output is not registered: {selected_id}") from exc
        if expected_type is not None and not isinstance(value, expected_type):
            raise ExecutionStateError(
                f"runtime stage output {selected_id!r} must be {expected_type.__name__}; "
                f"got {type(value).__name__}"
            )
        return value

    def resolve(self, output_ids: Sequence[str]) -> tuple[object, ...]:
        selected = tuple(_text(value, "output_ids[]") for value in output_ids)
        if len(selected) != len(set(selected)):
            raise ExecutionStateError("runtime stage input IDs must be unique")
        return tuple(self.get(output_id) for output_id in selected)

    def output_ids(self) -> tuple[str, ...]:
        return tuple(self._objects)


def can_publish(state: ExecutionState) -> bool:
    """Return true only for a complete, successful, non-resumable execution."""
    return state.terminal and not state.resumable and state.next_stage is None