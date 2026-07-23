"""Deterministic end-to-end pipeline runner for MO-021C.

The runner is orchestration-only.  It executes the existing Intelligence Layer
stage adapters in the governed order, captures immutable stage outputs and
trace summaries, and preserves repeated runs for determinism evaluation.  It
contains no insurance reasoning, scoring, or assertion logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Callable, Iterable, Mapping

from insurance_intelligence.evaluation.fixtures import PipelineFixture


PIPELINE_STAGE_ORDER = (
    "INTENT_ANALYZER",
    "CONTEXT_BUILDER",
    "REASONING_PLANNER",
    "EVIDENCE_RESOLVER",
    "REASONING_ENGINE",
    "DECISION_GATE",
    "EXPLANATION_GENERATOR",
    "RESPONSE_ASSEMBLER",
)


class EvaluationRunnerError(ValueError):
    """Raised when deterministic pipeline execution cannot proceed."""


StageExecutor = Callable[[PipelineFixture, Mapping[str, object]], object]


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _extract_status(output: object) -> str:
    for name in (
        "response_status",
        "explanation_status",
        "decision",
        "reasoning_status",
        "resolution_status",
        "plan_status",
        "context_status",
        "intent_status",
        "status",
    ):
        value = getattr(output, name, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if isinstance(output, Mapping):
        for name in (
            "response_status",
            "explanation_status",
            "decision",
            "reasoning_status",
            "resolution_status",
            "plan_status",
            "context_status",
            "intent_status",
            "status",
        ):
            value = output.get(name)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return type(output).__name__


def _extract_trace_events(output: object) -> tuple[str, ...]:
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
        value = getattr(output, name, None)
        if value is not None:
            trace = value
            break
    if trace is None and isinstance(output, Mapping):
        for name in candidates:
            if name in output:
                trace = output[name]
                break
    if trace is None:
        return ()
    events: list[str] = []
    for item in trace:  # type: ignore[union-attr]
        event = getattr(item, "event_type", None)
        if event is None and isinstance(item, Mapping):
            event = item.get("event_type")
        if isinstance(event, str) and event.strip():
            events.append(event.strip())
    return tuple(events)


@dataclass(frozen=True)
class StageExecution:
    stage: str
    sequence: int
    status: str
    output: object
    trace_events: tuple[str, ...]
    execution_id: str


@dataclass(frozen=True)
class PipelineRun:
    run_id: str
    fixture_id: str
    scenario_id: str
    scenario_version: str
    request_id: str
    run_number: int
    stage_executions: tuple[StageExecution, ...]
    completed: bool
    failed_stage: str | None
    failure_reason: str | None

    @property
    def final_output(self) -> object | None:
        return self.stage_executions[-1].output if self.stage_executions else None

    @property
    def final_status(self) -> str | None:
        return self.stage_executions[-1].status if self.stage_executions else None

    def stage(self, stage_name: str) -> StageExecution:
        for execution in self.stage_executions:
            if execution.stage == stage_name:
                return execution
        raise EvaluationRunnerError(f"stage was not executed: {stage_name}")


@dataclass(frozen=True)
class FixtureExecution:
    execution_id: str
    fixture_id: str
    scenario_id: str
    scenario_version: str
    runs: tuple[PipelineRun, ...]


class PipelineRunner:
    """Run explicit stage adapters in the canonical Intelligence Layer order."""

    def __init__(self, stage_executors: Mapping[str, StageExecutor]) -> None:
        if not isinstance(stage_executors, Mapping):
            raise EvaluationRunnerError("stage_executors must be a mapping")
        unknown = set(stage_executors) - set(PIPELINE_STAGE_ORDER)
        if unknown:
            raise EvaluationRunnerError(f"unknown pipeline stages: {sorted(unknown)}")
        missing = set(PIPELINE_STAGE_ORDER) - set(stage_executors)
        if missing:
            raise EvaluationRunnerError(f"missing pipeline stages: {sorted(missing)}")
        for stage, executor in stage_executors.items():
            if not callable(executor):
                raise EvaluationRunnerError(f"stage executor must be callable: {stage}")
        self._executors = MappingProxyType(dict(stage_executors))

    @property
    def stage_order(self) -> tuple[str, ...]:
        return PIPELINE_STAGE_ORDER

    def run_fixture(self, fixture: PipelineFixture) -> FixtureExecution:
        if not isinstance(fixture, PipelineFixture):
            raise EvaluationRunnerError("fixture must be a PipelineFixture")
        runs = tuple(self._run_once(fixture, number) for number in range(1, fixture.repeat_count + 1))
        return FixtureExecution(
            execution_id=_stable_id(
                "fixture-execution", fixture.fixture_id, fixture.request_id, fixture.repeat_count
            ),
            fixture_id=fixture.fixture_id,
            scenario_id=fixture.scenario_id,
            scenario_version=fixture.scenario_version,
            runs=runs,
        )

    def run_all(self, fixtures: Iterable[PipelineFixture]) -> tuple[FixtureExecution, ...]:
        values = tuple(fixtures)
        if any(not isinstance(item, PipelineFixture) for item in values):
            raise EvaluationRunnerError("fixtures must contain PipelineFixture values")
        keys = [(item.scenario_id, item.scenario_version) for item in values]
        if len(keys) != len(set(keys)):
            raise EvaluationRunnerError("fixtures must be unique by scenario identity")
        ordered = sorted(values, key=lambda item: (item.scenario_id, item.scenario_version))
        return tuple(self.run_fixture(item) for item in ordered)

    def _run_once(self, fixture: PipelineFixture, run_number: int) -> PipelineRun:
        outputs: dict[str, object] = {}
        executions: list[StageExecution] = []
        failed_stage: str | None = None
        failure_reason: str | None = None

        for sequence, stage in enumerate(PIPELINE_STAGE_ORDER, start=1):
            executor = self._executors[stage]
            try:
                output = executor(fixture, MappingProxyType(dict(outputs)))
                if output is None:
                    raise EvaluationRunnerError("stage returned no output")
            except Exception as exc:  # fail closed and preserve the first failure
                failed_stage = stage
                failure_reason = f"{type(exc).__name__}: {exc}"
                break
            status = _extract_status(output)
            executions.append(
                StageExecution(
                    stage=stage,
                    sequence=sequence,
                    status=status,
                    output=output,
                    trace_events=_extract_trace_events(output),
                    execution_id=_stable_id(
                        "stage-execution",
                        fixture.fixture_id,
                        fixture.request_id,
                        run_number,
                        stage,
                        status,
                    ),
                )
            )
            outputs[stage] = output

        completed = failed_stage is None and len(executions) == len(PIPELINE_STAGE_ORDER)
        return PipelineRun(
            run_id=_stable_id("pipeline-run", fixture.fixture_id, fixture.request_id, run_number),
            fixture_id=fixture.fixture_id,
            scenario_id=fixture.scenario_id,
            scenario_version=fixture.scenario_version,
            request_id=fixture.request_id,
            run_number=run_number,
            stage_executions=tuple(executions),
            completed=completed,
            failed_stage=failed_stage,
            failure_reason=failure_reason,
        )
