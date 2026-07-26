"""Executable deterministic evaluation service and baseline report (MO-021E).

The service composes the registered evaluation scenarios, explicit fixtures,
pipeline runner, and transparent assertion engine.  It measures the existing
Intelligence Layer without changing any stage behavior or generating insurance
content.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence

from insurance_intelligence.contracts.evaluation import EvaluationResult, EvaluationScenario
from insurance_intelligence.evaluation.assertions import EvaluationAssertionEngine
from insurance_intelligence.evaluation.fixtures import (
    PipelineFixture,
    PipelineFixtureRegistry,
    build_default_fixture_registry,
)
from insurance_intelligence.evaluation.runner import FixtureExecution, PipelineRunner, StageExecutor
from insurance_intelligence.evaluation.scenarios import (
    EvaluationScenarioRegistry,
    build_default_registry,
)


BASELINE_STATUSES = frozenset({"PASS", "FAIL", "BLOCKED", "MIXED"})


class EvaluationServiceError(ValueError):
    """Raised when an executable evaluation baseline cannot be produced."""


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


@dataclass(frozen=True)
class ScenarioBaseline:
    scenario_id: str
    scenario_version: str
    fixture_id: str
    execution_id: str
    result: EvaluationResult
    run_count: int


@dataclass(frozen=True)
class EvaluationBaselineReport:
    report_id: str
    status: str
    scenario_baselines: tuple[ScenarioBaseline, ...]
    scenario_count: int
    pass_count: int
    fail_count: int
    blocked_count: int
    invalid_count: int
    assertion_count: int
    passed_assertion_count: int
    failed_assertion_count: int
    pass_rate: float
    scenario_outcomes: Mapping[str, str]
    scenario_order: tuple[str, ...]


class EvaluationService:
    """Run and aggregate deterministic end-to-end evaluation scenarios."""

    def __init__(
        self,
        *,
        stage_executors: Mapping[str, StageExecutor] | None = None,
        runner: PipelineRunner | None = None,
        assertion_engine: EvaluationAssertionEngine | None = None,
        scenario_registry: EvaluationScenarioRegistry | None = None,
        fixture_registry: PipelineFixtureRegistry | None = None,
    ) -> None:
        if runner is not None and stage_executors is not None:
            raise EvaluationServiceError("provide runner or stage_executors, not both")
        if runner is None:
            if stage_executors is None:
                raise EvaluationServiceError("stage_executors are required when runner is not provided")
            runner = PipelineRunner(stage_executors)
        if not isinstance(runner, PipelineRunner):
            raise EvaluationServiceError("runner must be a PipelineRunner")
        if assertion_engine is not None and not isinstance(assertion_engine, EvaluationAssertionEngine):
            raise EvaluationServiceError("assertion_engine must be an EvaluationAssertionEngine")
        if scenario_registry is not None and not isinstance(scenario_registry, EvaluationScenarioRegistry):
            raise EvaluationServiceError("scenario_registry must be an EvaluationScenarioRegistry")
        if fixture_registry is not None and not isinstance(fixture_registry, PipelineFixtureRegistry):
            raise EvaluationServiceError("fixture_registry must be a PipelineFixtureRegistry")

        self._scenario_registry = scenario_registry or build_default_registry()
        self._fixture_registry = fixture_registry or build_default_fixture_registry(self._scenario_registry)
        self._runner = runner
        self._assertion_engine = assertion_engine or EvaluationAssertionEngine()

    def run_baseline(
        self,
        *,
        scenario_ids: Iterable[str] = (),
        tags: Iterable[str] = (),
        scenario_kind: str | None = None,
    ) -> EvaluationBaselineReport:
        scenarios = self._select_scenarios(
            scenario_ids=tuple(scenario_ids), tags=tuple(tags), scenario_kind=scenario_kind
        )
        if not scenarios:
            raise EvaluationServiceError("evaluation selection must contain at least one scenario")
        fixtures = tuple(self._fixture_registry.get(item.scenario_id) for item in scenarios)
        self._validate_alignment(scenarios, fixtures)
        executions = self._runner.run_all(fixtures)
        results = self._assertion_engine.evaluate_all(scenarios, executions)
        return self._build_report(scenarios, fixtures, executions, results)

    def run_scenario(self, scenario_id: str) -> ScenarioBaseline:
        report = self.run_baseline(scenario_ids=(scenario_id,))
        return report.scenario_baselines[0]

    def _select_scenarios(
        self,
        *,
        scenario_ids: Sequence[str],
        tags: Sequence[str],
        scenario_kind: str | None,
    ) -> tuple[EvaluationScenario, ...]:
        if len(scenario_ids) != len(set(scenario_ids)):
            raise EvaluationServiceError("scenario_ids must be unique")
        selected = self._scenario_registry.select(tags=tags, scenario_kind=scenario_kind)
        if scenario_ids:
            wanted = set(scenario_ids)
            selected = tuple(item for item in selected if item.scenario_id in wanted)
            missing = wanted - {item.scenario_id for item in selected}
            if missing:
                raise EvaluationServiceError(f"unknown or filtered scenario_ids: {sorted(missing)}")
        return tuple(selected)

    @staticmethod
    def _validate_alignment(
        scenarios: Sequence[EvaluationScenario], fixtures: Sequence[PipelineFixture]
    ) -> None:
        scenario_keys = tuple((item.scenario_id, item.scenario_version) for item in scenarios)
        fixture_keys = tuple((item.scenario_id, item.scenario_version) for item in fixtures)
        if len(scenario_keys) != len(set(scenario_keys)):
            raise EvaluationServiceError("scenarios must be unique by identity")
        if len(fixture_keys) != len(set(fixture_keys)):
            raise EvaluationServiceError("fixtures must be unique by identity")
        if set(scenario_keys) != set(fixture_keys):
            raise EvaluationServiceError("scenario and fixture identities must match exactly")

    @staticmethod
    def _build_report(
        scenarios: Sequence[EvaluationScenario],
        fixtures: Sequence[PipelineFixture],
        executions: Sequence[FixtureExecution],
        results: Sequence[EvaluationResult],
    ) -> EvaluationBaselineReport:
        scenario_map = {(item.scenario_id, item.scenario_version): item for item in scenarios}
        fixture_map = {(item.scenario_id, item.scenario_version): item for item in fixtures}
        execution_map = {(item.scenario_id, item.scenario_version): item for item in executions}
        result_map = {item.scenario_id: item for item in results}
        keys = tuple(sorted(scenario_map))
        if set(keys) != set(fixture_map) or set(keys) != set(execution_map):
            raise EvaluationServiceError("scenario, fixture, and execution identities must match")
        if {key[0] for key in keys} != set(result_map):
            raise EvaluationServiceError("scenario and result identities must match")

        baselines = tuple(
            ScenarioBaseline(
                scenario_id=key[0],
                scenario_version=key[1],
                fixture_id=fixture_map[key].fixture_id,
                execution_id=execution_map[key].execution_id,
                result=result_map[key[0]],
                run_count=len(execution_map[key].runs),
            )
            for key in keys
        )
        outcomes = {item.scenario_id: item.result.outcome for item in baselines}
        pass_count = sum(value == "PASS" for value in outcomes.values())
        fail_count = sum(value == "FAIL" for value in outcomes.values())
        blocked_count = sum(value == "BLOCKED" for value in outcomes.values())
        invalid_count = sum(value == "INVALID" for value in outcomes.values())
        assertion_results = tuple(
            assertion
            for baseline in baselines
            for assertion in baseline.result.assertion_results
        )
        passed_assertions = sum(item.passed for item in assertion_results)
        failed_assertions = len(assertion_results) - passed_assertions
        scenario_count = len(baselines)
        if pass_count == scenario_count:
            status = "PASS"
        elif blocked_count == scenario_count:
            status = "BLOCKED"
        elif fail_count + invalid_count == scenario_count:
            status = "FAIL"
        else:
            status = "MIXED"
        order = tuple(item.scenario_id for item in baselines)
        report_id = _stable_id(
            "evaluation-baseline",
            *(f"{item.scenario_id}@{item.scenario_version}:{item.result.outcome}" for item in baselines),
        )
        return EvaluationBaselineReport(
            report_id=report_id,
            status=status,
            scenario_baselines=baselines,
            scenario_count=scenario_count,
            pass_count=pass_count,
            fail_count=fail_count,
            blocked_count=blocked_count,
            invalid_count=invalid_count,
            assertion_count=len(assertion_results),
            passed_assertion_count=passed_assertions,
            failed_assertion_count=failed_assertions,
            pass_rate=pass_count / scenario_count,
            scenario_outcomes=MappingProxyType(outcomes),
            scenario_order=order,
        )
