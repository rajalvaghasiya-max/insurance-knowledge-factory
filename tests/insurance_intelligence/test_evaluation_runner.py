from dataclasses import FrozenInstanceError, dataclass

import pytest

from insurance_intelligence.evaluation.fixtures import build_default_fixture_registry
from insurance_intelligence.evaluation.runner import (
    PIPELINE_STAGE_ORDER,
    EvaluationRunnerError,
    PipelineRunner,
)


@dataclass(frozen=True)
class _Trace:
    event_type: str


@dataclass(frozen=True)
class _Output:
    status: str
    trace: tuple[_Trace, ...]
    stage: str
    request_id: str


def _executors(*, fail_stage=None, record=None):
    calls = record if record is not None else []

    def make(stage):
        def execute(fixture, previous):
            calls.append((stage, tuple(previous)))
            if stage == fail_stage:
                raise RuntimeError("synthetic stage failure")
            expected_previous = PIPELINE_STAGE_ORDER[: PIPELINE_STAGE_ORDER.index(stage)]
            assert tuple(previous) == expected_previous
            return _Output(
                status=f"{stage}_COMPLETE",
                trace=(_Trace(f"{stage}_STARTED"), _Trace(f"{stage}_COMPLETED")),
                stage=stage,
                request_id=fixture.request_id,
            )
        return execute

    return {stage: make(stage) for stage in PIPELINE_STAGE_ORDER}


def _fixture(scenario_id="star_copay_general_explanation"):
    return build_default_fixture_registry().get(scenario_id)


def test_runner_executes_all_stages_in_canonical_order():
    calls = []
    output = PipelineRunner(_executors(record=calls)).run_fixture(_fixture())
    assert output.runs[0].completed is True
    assert [item.stage for item in output.runs[0].stage_executions] == list(PIPELINE_STAGE_ORDER)
    assert [item[0] for item in calls] == list(PIPELINE_STAGE_ORDER)


def test_runner_preserves_scenario_and_request_identity():
    fixture = _fixture()
    output = PipelineRunner(_executors()).run_fixture(fixture)
    run = output.runs[0]
    assert output.fixture_id == fixture.fixture_id
    assert output.scenario_id == fixture.scenario_id
    assert run.request_id == fixture.request_id


def test_stage_status_is_captured():
    run = PipelineRunner(_executors()).run_fixture(_fixture()).runs[0]
    assert run.stage("DECISION_GATE").status == "DECISION_GATE_COMPLETE"
    assert run.final_status == "RESPONSE_ASSEMBLER_COMPLETE"


def test_stage_trace_events_are_captured():
    run = PipelineRunner(_executors()).run_fixture(_fixture()).runs[0]
    assert run.stage("EVIDENCE_RESOLVER").trace_events == (
        "EVIDENCE_RESOLVER_STARTED",
        "EVIDENCE_RESOLVER_COMPLETED",
    )


def test_final_output_is_last_stage_output():
    run = PipelineRunner(_executors()).run_fixture(_fixture()).runs[0]
    assert run.final_output.stage == "RESPONSE_ASSEMBLER"


def test_failure_is_fail_closed_and_stops_later_stages():
    run = PipelineRunner(_executors(fail_stage="EVIDENCE_RESOLVER")).run_fixture(_fixture()).runs[0]
    assert run.completed is False
    assert run.failed_stage == "EVIDENCE_RESOLVER"
    assert "synthetic stage failure" in run.failure_reason
    assert [item.stage for item in run.stage_executions] == list(PIPELINE_STAGE_ORDER[:3])


def test_stage_returning_none_fails_closed():
    executors = _executors()
    executors["CONTEXT_BUILDER"] = lambda fixture, previous: None
    run = PipelineRunner(executors).run_fixture(_fixture()).runs[0]
    assert run.failed_stage == "CONTEXT_BUILDER"
    assert "stage returned no output" in run.failure_reason


def test_determinism_fixture_runs_twice():
    output = PipelineRunner(_executors()).run_fixture(_fixture("star_copay_determinism"))
    assert len(output.runs) == 2
    assert [item.run_number for item in output.runs] == [1, 2]


def test_non_determinism_fixture_runs_once():
    output = PipelineRunner(_executors()).run_fixture(_fixture())
    assert len(output.runs) == 1


def test_repeated_runs_have_distinct_run_ids():
    output = PipelineRunner(_executors()).run_fixture(_fixture("star_copay_determinism"))
    assert output.runs[0].run_id != output.runs[1].run_id


def test_repeated_runs_have_identical_stage_statuses():
    output = PipelineRunner(_executors()).run_fixture(_fixture("star_copay_determinism"))
    assert tuple(item.status for item in output.runs[0].stage_executions) == tuple(
        item.status for item in output.runs[1].stage_executions
    )


def test_run_ids_are_deterministic():
    runner = PipelineRunner(_executors())
    first = runner.run_fixture(_fixture())
    second = runner.run_fixture(_fixture())
    assert first.execution_id == second.execution_id
    assert first.runs[0].run_id == second.runs[0].run_id


def test_stage_execution_ids_are_deterministic():
    runner = PipelineRunner(_executors())
    first = runner.run_fixture(_fixture()).runs[0]
    second = runner.run_fixture(_fixture()).runs[0]
    assert tuple(item.execution_id for item in first.stage_executions) == tuple(
        item.execution_id for item in second.stage_executions
    )


def test_run_all_orders_fixtures_by_scenario_identity():
    registry = build_default_fixture_registry()
    fixtures = tuple(reversed(registry.all_fixtures()[:3]))
    outputs = PipelineRunner(_executors()).run_all(fixtures)
    assert [item.scenario_id for item in outputs] == sorted(item.scenario_id for item in fixtures)


def test_run_all_rejects_duplicate_scenario_identity():
    fixture = _fixture()
    with pytest.raises(EvaluationRunnerError, match="unique"):
        PipelineRunner(_executors()).run_all((fixture, fixture))


def test_missing_stage_executor_is_rejected():
    executors = _executors()
    executors.pop("RESPONSE_ASSEMBLER")
    with pytest.raises(EvaluationRunnerError, match="missing pipeline stages"):
        PipelineRunner(executors)


def test_unknown_stage_executor_is_rejected():
    executors = _executors()
    executors["UNKNOWN"] = lambda fixture, previous: object()
    with pytest.raises(EvaluationRunnerError, match="unknown pipeline stages"):
        PipelineRunner(executors)


def test_non_callable_stage_executor_is_rejected():
    executors = _executors()
    executors["INTENT_ANALYZER"] = object()
    with pytest.raises(EvaluationRunnerError, match="callable"):
        PipelineRunner(executors)


def test_invalid_fixture_is_rejected():
    with pytest.raises(EvaluationRunnerError, match="PipelineFixture"):
        PipelineRunner(_executors()).run_fixture(object())


def test_stage_lookup_rejects_unexecuted_stage():
    run = PipelineRunner(_executors(fail_stage="CONTEXT_BUILDER")).run_fixture(_fixture()).runs[0]
    with pytest.raises(EvaluationRunnerError, match="not executed"):
        run.stage("RESPONSE_ASSEMBLER")


def test_output_objects_are_immutable():
    output = PipelineRunner(_executors()).run_fixture(_fixture())
    with pytest.raises(FrozenInstanceError):
        output.scenario_id = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        output.runs[0].completed = False  # type: ignore[misc]


def test_previous_stage_mapping_is_read_only():
    def first(fixture, previous):
        with pytest.raises(TypeError):
            previous["X"] = object()
        return _Output("OK", (), "INTENT_ANALYZER", fixture.request_id)

    executors = _executors()
    executors["INTENT_ANALYZER"] = first
    assert PipelineRunner(executors).run_fixture(_fixture()).runs[0].completed


def test_runner_does_not_score_scenario_assertions():
    output = PipelineRunner(_executors()).run_fixture(_fixture())
    assert not hasattr(output, "assertion_results")
    assert not hasattr(output.runs[0], "evaluation_outcome")


def test_runner_does_not_add_reasoning_or_response_content():
    output = PipelineRunner(_executors()).run_fixture(_fixture())
    assert not hasattr(output, "findings")
    assert not hasattr(output, "response")
