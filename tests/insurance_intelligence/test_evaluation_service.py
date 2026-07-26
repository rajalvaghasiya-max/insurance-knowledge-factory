from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from insurance_intelligence.contracts.evaluation import build_assertion, build_scenario, build_stage_expectation
from insurance_intelligence.evaluation.fixtures import PipelineFixtureRegistry, build_fixture
from insurance_intelligence.evaluation.runner import PIPELINE_STAGE_ORDER, PipelineRunner
from insurance_intelligence.evaluation.scenarios import EvaluationScenarioRegistry
from insurance_intelligence.evaluation.service import (
    EvaluationBaselineReport,
    EvaluationService,
    EvaluationServiceError,
)


def _scenario(scenario_id: str = "scenario_a", *, behavior: str = "preserve_percentage"):
    return build_scenario(
        scenario_id=scenario_id,
        scenario_version="1.0",
        name=scenario_id,
        description=scenario_id,
        scenario_kind="GENERAL_EXPLANATION",
        request_text="Explain the clause.",
        domain="health",
        topic="conditional_copayment",
        audience="CUSTOMER",
        expected_response_statuses=("ANSWER",),
        stage_expectations=(
            build_stage_expectation(stage="DECISION_GATE", expected_statuses=("APPROVED",)),
            build_stage_expectation(stage="RESPONSE_ASSEMBLER", expected_statuses=("ANSWER",)),
        ),
        assertions=(
            build_assertion(
                assertion_id=f"{scenario_id}:response",
                category="RESPONSE_STATUS",
                description="response",
                target_stage="RESPONSE_ASSEMBLER",
                expected_values=("ANSWER",),
            ),
            build_assertion(
                assertion_id=f"{scenario_id}:behavior",
                category="REQUIRED_BEHAVIOR",
                description="behavior",
                expected_values=(behavior,),
            ),
        ),
        required_behaviors=(behavior,),
        prohibited_behaviors=("recommend_product",),
        tags=("baseline",),
        priority=10,
    )


def _executors(*, response_status: str = "ANSWER", behavior: str = "preserve_percentage", fail_stage=None):
    def executor(stage):
        def run(fixture, outputs):
            if stage == fail_stage:
                raise RuntimeError("stage failure")
            status = {
                "INTENT_ANALYZER": "IN_SCOPE",
                "CONTEXT_BUILDER": "ANSWERABLE",
                "REASONING_PLANNER": "READY",
                "EVIDENCE_RESOLVER": "RESOLVED",
                "REASONING_ENGINE": "REASONED",
                "DECISION_GATE": "APPROVED",
                "EXPLANATION_GENERATOR": "DRAFTED",
                "RESPONSE_ASSEMBLER": response_status,
            }[stage]
            return {
                "status": status,
                "response_status": status if stage == "RESPONSE_ASSEMBLER" else None,
                "behaviors": (behavior,),
                "response_id": f"response:{fixture.scenario_id}",
                "audience": fixture.audience,
                "response_format": "PLAIN",
                "sections": ({"section_type": "DIRECT_ANSWER"},),
                "trace": ({"event_type": f"{stage}_COMPLETED"},),
            }
        return run

    return {stage: executor(stage) for stage in PIPELINE_STAGE_ORDER}


def _service(*, scenarios=None, executors=None):
    scenario_values = tuple(scenarios or (_scenario(),))
    scenario_registry = EvaluationScenarioRegistry(scenario_values)
    fixture_registry = PipelineFixtureRegistry(build_fixture(item) for item in scenario_values)
    return EvaluationService(
        stage_executors=executors or _executors(),
        scenario_registry=scenario_registry,
        fixture_registry=fixture_registry,
    )


def test_service_requires_runner_or_executors():
    with pytest.raises(EvaluationServiceError):
        EvaluationService()


def test_service_rejects_runner_and_executors_together():
    runner = PipelineRunner(_executors())
    with pytest.raises(EvaluationServiceError):
        EvaluationService(runner=runner, stage_executors=_executors())


def test_run_single_scenario_passes():
    baseline = _service().run_scenario("scenario_a")
    assert baseline.result.outcome == "PASS"
    assert baseline.run_count == 1


def test_run_baseline_aggregates_pass_counts():
    report = _service(scenarios=(_scenario("b"), _scenario("a"))).run_baseline()
    assert report.status == "PASS"
    assert report.scenario_count == 2
    assert report.pass_count == 2
    assert report.pass_rate == 1.0
    assert report.scenario_order == ("a", "b")


def test_report_assertion_counts_are_aggregated():
    report = _service().run_baseline()
    assert report.assertion_count == 4
    assert report.passed_assertion_count == 4
    assert report.failed_assertion_count == 0


def test_failed_assertion_produces_fail_report():
    report = _service(executors=_executors(response_status="BLOCKED")).run_baseline()
    assert report.status == "FAIL"
    assert report.fail_count == 1
    assert report.pass_rate == 0.0


def test_stage_failure_produces_blocked_report():
    report = _service(executors=_executors(fail_stage="EVIDENCE_RESOLVER")).run_baseline()
    assert report.status == "BLOCKED"
    assert report.blocked_count == 1
    assert report.scenario_baselines[0].result.blocked_reason


def test_mixed_outcomes_produce_mixed_report():
    scenarios = (_scenario("a", behavior="one"), _scenario("b", behavior="two"))
    executors = _executors(behavior="one")
    report = _service(scenarios=scenarios, executors=executors).run_baseline()
    assert report.status == "MIXED"
    assert report.pass_count == 1
    assert report.fail_count == 1


def test_selection_by_scenario_id():
    report = _service(scenarios=(_scenario("a"), _scenario("b"))).run_baseline(scenario_ids=("b",))
    assert report.scenario_order == ("b",)


def test_selection_rejects_duplicate_ids():
    with pytest.raises(EvaluationServiceError):
        _service().run_baseline(scenario_ids=("scenario_a", "scenario_a"))


def test_selection_rejects_unknown_id():
    with pytest.raises(EvaluationServiceError):
        _service().run_baseline(scenario_ids=("missing",))


def test_selection_by_tag():
    report = _service().run_baseline(tags=("baseline",))
    assert report.scenario_count == 1


def test_empty_filtered_selection_is_rejected():
    with pytest.raises(EvaluationServiceError):
        _service().run_baseline(tags=("missing",))


def test_report_id_is_deterministic():
    service = _service()
    assert service.run_baseline().report_id == service.run_baseline().report_id


def test_scenario_outcomes_are_immutable():
    report = _service().run_baseline()
    assert isinstance(report.scenario_outcomes, MappingProxyType)
    with pytest.raises(TypeError):
        report.scenario_outcomes["x"] = "FAIL"  # type: ignore[index]


def test_report_is_frozen():
    report = _service().run_baseline()
    with pytest.raises(FrozenInstanceError):
        report.status = "FAIL"  # type: ignore[misc]


def test_scenario_baseline_is_frozen():
    baseline = _service().run_scenario("scenario_a")
    with pytest.raises(FrozenInstanceError):
        baseline.run_count = 9  # type: ignore[misc]


def test_runner_can_be_injected():
    service = EvaluationService(
        runner=PipelineRunner(_executors()),
        scenario_registry=EvaluationScenarioRegistry((_scenario(),)),
        fixture_registry=PipelineFixtureRegistry((build_fixture(_scenario()),)),
    )
    assert service.run_baseline().status == "PASS"


def test_repeat_count_is_preserved_for_determinism_fixture():
    scenario = _scenario()
    fixture = build_fixture(scenario, repeat_count=2)
    service = EvaluationService(
        stage_executors=_executors(),
        scenario_registry=EvaluationScenarioRegistry((scenario,)),
        fixture_registry=PipelineFixtureRegistry((fixture,)),
    )
    assert service.run_scenario(scenario.scenario_id).run_count == 2


def test_baseline_report_type():
    assert isinstance(_service().run_baseline(), EvaluationBaselineReport)


def test_no_pipeline_output_is_mutated():
    report = _service().run_baseline()
    before = report.scenario_baselines[0].result
    _service().run_baseline()
    assert report.scenario_baselines[0].result == before


def test_scenario_order_does_not_depend_on_registration_order():
    first = _service(scenarios=(_scenario("b"), _scenario("a"))).run_baseline()
    second = _service(scenarios=(_scenario("a"), _scenario("b"))).run_baseline()
    assert first.scenario_order == second.scenario_order == ("a", "b")


def test_report_contains_no_response_generation_fields():
    fields = set(EvaluationBaselineReport.__dataclass_fields__)
    assert not {"answer", "explanation", "recommendation", "example"} & fields


def test_service_does_not_require_network_or_llm_configuration():
    report = _service().run_baseline()
    assert report.status == "PASS"
