"""Transparent assertion scoring for deterministic end-to-end evaluation (MO-021D).

The assertion engine consumes only registered scenario expectations and captured
pipeline runs.  It never executes or modifies the pipeline.  Every decision is
returned as an explicit :class:`AssertionResult`.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from hashlib import sha256
from typing import Iterable, Mapping, Sequence

from insurance_intelligence.contracts.evaluation import (
    AssertionResult,
    EvaluationAssertion,
    EvaluationResult,
    EvaluationScenario,
    build_assertion_result,
    build_result,
)
from insurance_intelligence.evaluation.runner import FixtureExecution, PipelineRun


class EvaluationAssertionError(ValueError):
    """Raised when captured runs cannot be scored deterministically."""


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _read(value: object, name: str, default: object = None) -> object:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _strings(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, Mapping):
        return tuple(sorted(str(key) for key, item in value.items() if bool(item)))
    try:
        result = tuple(str(item).strip() for item in value if str(item).strip())  # type: ignore[union-attr]
    except TypeError:
        return ()
    return tuple(dict.fromkeys(result))


def _observed_behaviors(run: PipelineRun) -> tuple[str, ...]:
    observed: set[str] = set()
    for execution in run.stage_executions:
        output = execution.output
        for name in (
            "behaviors",
            "observed_behaviors",
            "behavior_flags",
            "evaluation_behaviors",
        ):
            observed.update(_strings(_read(output, name)))
    return tuple(sorted(observed))


def _canonical(value: object) -> object:
    """Return a deterministic comparison representation, excluding runtime IDs."""
    excluded = {
        "run_id",
        "execution_id",
        "trace_id",
        "order_marker",
        "created_at",
        "timestamp",
    }
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return tuple(
            (str(key), _canonical(item))
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in excluded
        )
    if isinstance(value, (tuple, list)):
        return tuple(_canonical(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((_canonical(item) for item in value), key=repr))
    if is_dataclass(value):
        return tuple(
            (field.name, _canonical(getattr(value, field.name)))
            for field in fields(value)
            if field.name not in excluded
        )
    if hasattr(value, "__dict__"):
        return _canonical(vars(value))
    return repr(value)


def _response_identity(run: PipelineRun) -> tuple[str, ...]:
    output = run.final_output
    values: list[str] = []
    for name in ("response_id", "response_status", "audience", "response_format"):
        item = _read(output, name)
        if isinstance(item, str) and item.strip():
            values.append(item.strip())
    return tuple(values)


def _section_order(run: PipelineRun) -> tuple[str, ...]:
    sections = _read(run.final_output, "sections", ())
    result: list[str] = []
    for section in sections or ():  # type: ignore[union-attr]
        value = _read(section, "section_type", _read(section, "section_id"))
        if isinstance(value, str) and value.strip():
            result.append(value.strip())
    return tuple(result)


def _all_trace_events(run: PipelineRun) -> tuple[str, ...]:
    return tuple(event for stage in run.stage_executions for event in stage.trace_events)


def _result(assertion: EvaluationAssertion, passed: bool, actual: Sequence[str], message: str) -> AssertionResult:
    return build_assertion_result(
        assertion_id=assertion.assertion_id,
        category=assertion.category,
        passed=passed,
        actual_values=tuple(dict.fromkeys(str(item) for item in actual)),
        message=message,
    )


class EvaluationAssertionEngine:
    """Score a captured fixture execution against one registered scenario."""

    def evaluate(self, scenario: EvaluationScenario, execution: FixtureExecution) -> EvaluationResult:
        if not isinstance(scenario, EvaluationScenario):
            raise EvaluationAssertionError("scenario must be an EvaluationScenario")
        if not isinstance(execution, FixtureExecution):
            raise EvaluationAssertionError("execution must be a FixtureExecution")
        if (scenario.scenario_id, scenario.scenario_version) != (
            execution.scenario_id,
            execution.scenario_version,
        ):
            raise EvaluationAssertionError("scenario and execution identity must match")
        if not execution.runs:
            return build_result(
                scenario_id=scenario.scenario_id,
                run_id=execution.execution_id,
                outcome="BLOCKED",
                assertion_results=(),
                blocked_reason="fixture execution contains no pipeline runs",
            )
        failed_runs = tuple(run for run in execution.runs if not run.completed)
        if failed_runs:
            reason = "; ".join(
                f"run {run.run_number} failed at {run.failed_stage}: {run.failure_reason}"
                for run in failed_runs
            )
            return build_result(
                scenario_id=scenario.scenario_id,
                run_id=execution.execution_id,
                outcome="BLOCKED",
                assertion_results=(),
                blocked_reason=reason,
            )

        results: list[AssertionResult] = []
        primary = execution.runs[0]
        for expectation in scenario.stage_expectations:
            stage = primary.stage(expectation.stage)
            status_pass = stage.status in expectation.expected_statuses
            results.append(
                build_assertion_result(
                    assertion_id=f"{scenario.scenario_id}:stage:{expectation.stage}:status",
                    category="STAGE_STATUS",
                    passed=status_pass,
                    actual_values=(stage.status,),
                    message=(
                        f"{expectation.stage} status matched"
                        if status_pass
                        else f"expected one of {expectation.expected_statuses}; got {stage.status}"
                    ),
                )
            )
            required_missing = tuple(
                event for event in expectation.required_trace_events if event not in stage.trace_events
            )
            prohibited_present = tuple(
                event for event in expectation.prohibited_trace_events if event in stage.trace_events
            )
            if expectation.required_trace_events or expectation.prohibited_trace_events:
                results.append(
                    build_assertion_result(
                        assertion_id=f"{scenario.scenario_id}:stage:{expectation.stage}:trace",
                        category="TRACE_EVENT",
                        passed=not required_missing and not prohibited_present,
                        actual_values=stage.trace_events,
                        message=(
                            "trace expectations matched"
                            if not required_missing and not prohibited_present
                            else f"missing={required_missing}; prohibited_present={prohibited_present}"
                        ),
                    )
                )

        for assertion in scenario.assertions:
            results.append(self._score_assertion(assertion, scenario, execution))

        failed = {result.assertion_id for result in results if not result.passed}
        outcome = "FAIL" if failed else "PASS"
        return build_result(
            scenario_id=scenario.scenario_id,
            run_id=execution.execution_id,
            outcome=outcome,
            assertion_results=tuple(results),
        )

    def evaluate_all(
        self,
        scenarios: Iterable[EvaluationScenario],
        executions: Iterable[FixtureExecution],
    ) -> tuple[EvaluationResult, ...]:
        scenario_values = tuple(scenarios)
        execution_values = tuple(executions)
        scenario_map = {(item.scenario_id, item.scenario_version): item for item in scenario_values}
        execution_map = {(item.scenario_id, item.scenario_version): item for item in execution_values}
        if len(scenario_map) != len(scenario_values):
            raise EvaluationAssertionError("scenarios must be unique by identity")
        if len(execution_map) != len(execution_values):
            raise EvaluationAssertionError("executions must be unique by identity")
        if set(scenario_map) != set(execution_map):
            raise EvaluationAssertionError("scenario and execution identities must match exactly")
        return tuple(self.evaluate(scenario_map[key], execution_map[key]) for key in sorted(scenario_map))

    def _score_assertion(
        self,
        assertion: EvaluationAssertion,
        scenario: EvaluationScenario,
        execution: FixtureExecution,
    ) -> AssertionResult:
        run = execution.runs[0]
        if assertion.category == "STAGE_STATUS":
            if assertion.target_stage is None:
                return _result(assertion, False, (), "target_stage is required")
            actual = (run.stage(assertion.target_stage).status,)
            return _result(assertion, bool(set(actual) & set(assertion.expected_values)), actual, "stage status evaluated")
        if assertion.category == "RESPONSE_STATUS":
            actual = (run.final_status,) if run.final_status else ()
            passed = bool(set(actual) & set(assertion.expected_values))
            return _result(assertion, passed, actual, "response status evaluated")
        if assertion.category in {"REQUIRED_BEHAVIOR", "PROHIBITED_BEHAVIOR"}:
            observed = set(_observed_behaviors(run))
            expected = set(assertion.expected_values)
            if assertion.category == "REQUIRED_BEHAVIOR":
                missing = tuple(sorted(expected - observed))
                return _result(assertion, not missing, tuple(sorted(observed)), f"missing required behaviors: {missing}" if missing else "required behaviors present")
            present = tuple(sorted(expected & observed))
            return _result(assertion, not present, tuple(sorted(observed)), f"prohibited behaviors present: {present}" if present else "prohibited behaviors absent")
        if assertion.category == "TRACE_EVENT":
            events = run.stage(assertion.target_stage).trace_events if assertion.target_stage else _all_trace_events(run)
            missing = tuple(item for item in assertion.expected_values if item not in events)
            return _result(assertion, not missing, events, f"missing trace events: {missing}" if missing else "trace events present")
        if assertion.category == "DETERMINISM":
            passed, actual, message = self._score_determinism(execution, assertion.expected_values)
            return _result(assertion, passed, actual, message)
        if assertion.category == "AUDIENCE_FORMAT":
            actual = _strings(_read(run.final_output, "audience")) + _strings(_read(run.final_output, "response_format"))
            passed = not assertion.expected_values or set(assertion.expected_values).issubset(set(actual))
            return _result(assertion, passed, actual, "audience format evaluated")
        if assertion.category in {
            "EVIDENCE_FIDELITY",
            "LIMITATION_FIDELITY",
            "CLARIFICATION_FIDELITY",
        }:
            marker_name = {
                "EVIDENCE_FIDELITY": "evidence_fidelity",
                "LIMITATION_FIDELITY": "limitation_fidelity",
                "CLARIFICATION_FIDELITY": "clarification_fidelity",
            }[assertion.category]
            marker = _read(run.final_output, marker_name)
            actual = _strings(marker)
            passed = marker is True or (bool(actual) and (not assertion.expected_values or set(assertion.expected_values).issubset(set(actual))))
            return _result(assertion, passed, actual or (str(marker),), f"{marker_name} evaluated")
        return _result(assertion, False, (), f"unsupported assertion category: {assertion.category}")

    def _score_determinism(
        self,
        execution: FixtureExecution,
        expected_values: Sequence[str],
    ) -> tuple[bool, tuple[str, ...], str]:
        if len(execution.runs) < 2:
            return False, (str(len(execution.runs)),), "determinism evaluation requires at least two runs"
        first = execution.runs[0]
        comparisons = {
            "identical_response_id": _response_identity(first) == _response_identity(execution.runs[1]),
            "identical_section_order": _section_order(first) == _section_order(execution.runs[1]),
            "identical_trace_order": _all_trace_events(first) == _all_trace_events(execution.runs[1]),
            "identical_output": _canonical(first.final_output) == _canonical(execution.runs[1].final_output),
            "nondeterministic_output": _canonical(first.final_output) != _canonical(execution.runs[1].final_output),
        }
        requested = tuple(expected_values) or ("identical_output",)
        unknown = tuple(item for item in requested if item not in comparisons)
        passed = not unknown and all(comparisons[item] for item in requested)
        actual = tuple(f"{item}={comparisons.get(item, False)}" for item in requested)
        message = "determinism expectations matched" if passed else f"unknown_or_failed={unknown or tuple(item for item in requested if not comparisons.get(item, False))}"
        return passed, actual, message
