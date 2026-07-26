from dataclasses import FrozenInstanceError, dataclass

import pytest

from insurance_intelligence.contracts.evaluation import build_assertion, build_scenario, build_stage_expectation
from insurance_intelligence.evaluation.assertions import EvaluationAssertionEngine, EvaluationAssertionError
from insurance_intelligence.evaluation.fixtures import build_default_fixture_registry
from insurance_intelligence.evaluation.runner import PIPELINE_STAGE_ORDER, PipelineRunner
from insurance_intelligence.evaluation.scenarios import build_default_registry


@dataclass(frozen=True)
class _Trace:
    event_type: str


@dataclass(frozen=True)
class _Section:
    section_type: str


@dataclass(frozen=True)
class _Output:
    status: str
    trace: tuple[_Trace, ...]
    behaviors: tuple[str, ...] = ()
    response_id: str | None = None
    sections: tuple[_Section, ...] = ()
    audience: str | None = None
    response_format: str | None = None
    evidence_fidelity: bool | None = None
    limitation_fidelity: bool | None = None
    clarification_fidelity: bool | None = None


def _scenario(scenario_id="star_copay_general_explanation"):
    return build_default_registry().get(scenario_id)


def _fixture(scenario_id="star_copay_general_explanation"):
    return build_default_fixture_registry().get(scenario_id)


def _executors(*, final_status="ANSWER", behaviors=(), final_factory=None, fail_stage=None):
    def make(stage):
        def execute(fixture, previous):
            if stage == fail_stage:
                raise RuntimeError("synthetic failure")
            if stage == "DECISION_GATE":
                return _Output("APPROVED", (_Trace("DECISION_COMPLETED"),))
            if stage == "RESPONSE_ASSEMBLER":
                if final_factory:
                    return final_factory(fixture)
                return _Output(
                    final_status,
                    (_Trace("RESPONSE_COMPLETED"),),
                    tuple(behaviors),
                    response_id="response-stable",
                    sections=(_Section("DIRECT_ANSWER"), _Section("EXPLANATION")),
                    audience=fixture.audience,
                    response_format="STANDARD",
                )
            return _Output(f"{stage}_COMPLETE", (_Trace(f"{stage}_COMPLETED"),))
        return execute
    return {stage: make(stage) for stage in PIPELINE_STAGE_ORDER}


def _execution(scenario_id="star_copay_general_explanation", **kwargs):
    return PipelineRunner(_executors(**kwargs)).run_fixture(_fixture(scenario_id))


def test_general_scenario_passes_when_required_behaviors_are_present():
    execution = _execution(
        behaviors=("preserve_percentage", "preserve_condition", "preserve_evidence")
    )
    result = EvaluationAssertionEngine().evaluate(_scenario(), execution)
    assert result.outcome == "PASS"
    assert not result.failed_assertion_ids


def test_response_status_mismatch_fails():
    result = EvaluationAssertionEngine().evaluate(
        _scenario(),
        _execution(final_status="BLOCKED", behaviors=("preserve_percentage", "preserve_condition", "preserve_evidence")),
    )
    assert result.outcome == "FAIL"
    assert any("response_status" in item for item in result.failed_assertion_ids)


def test_missing_required_behavior_fails():
    result = EvaluationAssertionEngine().evaluate(_scenario(), _execution(behaviors=("preserve_percentage",)))
    assert result.outcome == "FAIL"
    assertion = next(item for item in result.assertion_results if item.category == "REQUIRED_BEHAVIOR")
    assert assertion.passed is False
    assert "preserve_condition" in assertion.message


def test_prohibited_behavior_fails():
    result = EvaluationAssertionEngine().evaluate(
        _scenario(),
        _execution(behaviors=("preserve_percentage", "preserve_condition", "preserve_evidence", "recommend_product")),
    )
    assertion = next(item for item in result.assertion_results if item.category == "PROHIBITED_BEHAVIOR")
    assert assertion.passed is False


def test_stage_status_expectations_are_scored_explicitly():
    result = EvaluationAssertionEngine().evaluate(_scenario(), _execution(behaviors=("preserve_percentage", "preserve_condition", "preserve_evidence")))
    ids = {item.assertion_id for item in result.assertion_results}
    assert "star_copay_general_explanation:stage:DECISION_GATE:status" in ids
    assert "star_copay_general_explanation:stage:RESPONSE_ASSEMBLER:status" in ids


def test_pipeline_failure_returns_blocked_result():
    execution = PipelineRunner(_executors(fail_stage="EVIDENCE_RESOLVER")).run_fixture(_fixture())
    result = EvaluationAssertionEngine().evaluate(_scenario(), execution)
    assert result.outcome == "BLOCKED"
    assert "EVIDENCE_RESOLVER" in result.blocked_reason


def test_identity_mismatch_is_rejected():
    with pytest.raises(EvaluationAssertionError, match="identity"):
        EvaluationAssertionEngine().evaluate(_scenario(), _execution("star_copay_customer_format"))


def test_invalid_inputs_are_rejected():
    engine = EvaluationAssertionEngine()
    with pytest.raises(EvaluationAssertionError, match="EvaluationScenario"):
        engine.evaluate(object(), _execution())
    with pytest.raises(EvaluationAssertionError, match="FixtureExecution"):
        engine.evaluate(_scenario(), object())


def test_required_stage_trace_event_passes():
    scenario = build_scenario(
        scenario_id="trace_case", scenario_version="1.0", name="trace", description="trace",
        scenario_kind="GENERAL_EXPLANATION", request_text="trace", domain="health", topic="copay",
        audience="CUSTOMER", expected_response_statuses=("ANSWER",),
        stage_expectations=(build_stage_expectation(stage="RESPONSE_ASSEMBLER", expected_statuses=("ANSWER",), required_trace_events=("RESPONSE_COMPLETED",)),),
        assertions=(),
    )
    fixture = _fixture()
    execution = PipelineRunner(_executors()).run_fixture(fixture)
    # identity is intentionally rebuilt because the assertion engine is identity strict
    execution = type(execution)(execution.execution_id, execution.fixture_id, "trace_case", "1.0", execution.runs)
    result = EvaluationAssertionEngine().evaluate(scenario, execution)
    assert result.outcome == "PASS"


def test_missing_required_stage_trace_event_fails():
    scenario = build_scenario(
        scenario_id="trace_case", scenario_version="1.0", name="trace", description="trace",
        scenario_kind="GENERAL_EXPLANATION", request_text="trace", domain="health", topic="copay",
        audience="CUSTOMER", expected_response_statuses=("ANSWER",),
        stage_expectations=(build_stage_expectation(stage="RESPONSE_ASSEMBLER", expected_statuses=("ANSWER",), required_trace_events=("MISSING",)),),
        assertions=(),
    )
    execution = _execution()
    execution = type(execution)(execution.execution_id, execution.fixture_id, "trace_case", "1.0", execution.runs)
    result = EvaluationAssertionEngine().evaluate(scenario, execution)
    assert result.outcome == "FAIL"


def test_prohibited_stage_trace_event_fails():
    scenario = build_scenario(
        scenario_id="trace_case", scenario_version="1.0", name="trace", description="trace",
        scenario_kind="GENERAL_EXPLANATION", request_text="trace", domain="health", topic="copay",
        audience="CUSTOMER", expected_response_statuses=("ANSWER",),
        stage_expectations=(build_stage_expectation(stage="RESPONSE_ASSEMBLER", expected_statuses=("ANSWER",), prohibited_trace_events=("RESPONSE_COMPLETED",)),),
        assertions=(),
    )
    execution = _execution()
    execution = type(execution)(execution.execution_id, execution.fixture_id, "trace_case", "1.0", execution.runs)
    assert EvaluationAssertionEngine().evaluate(scenario, execution).outcome == "FAIL"


def test_determinism_assertion_passes_for_identical_repeated_outputs():
    scenario = _scenario("star_copay_determinism")
    execution = _execution(
        "star_copay_determinism",
        behaviors=("identical_response_id", "identical_section_order", "identical_trace_order"),
    )
    # default scenario expresses determinism as behavior labels; add explicit deterministic assertion
    explicit = build_assertion(assertion_id="det", category="DETERMINISM", description="det", expected_values=("identical_response_id", "identical_section_order", "identical_trace_order"))
    scenario = type(scenario)(*scenario.__dict__.values())
    scenario = type(scenario)(**{**scenario.__dict__, "assertions": scenario.assertions + (explicit,)})
    assert EvaluationAssertionEngine().evaluate(scenario, execution).outcome == "PASS"


def test_determinism_assertion_fails_when_outputs_differ():
    counter = {"value": 0}
    def factory(fixture):
        counter["value"] += 1
        return _Output("ANSWER", (_Trace("RESPONSE_COMPLETED"),), response_id=f"r{counter['value']}", sections=(_Section("DIRECT_ANSWER"),))
    execution = _execution("star_copay_determinism", final_factory=factory)
    base = _scenario("star_copay_determinism")
    explicit = build_assertion(assertion_id="det", category="DETERMINISM", description="det", expected_values=("identical_response_id",))
    scenario = type(base)(**{**base.__dict__, "assertions": (explicit,)})
    result = EvaluationAssertionEngine().evaluate(scenario, execution)
    assert result.outcome == "FAIL"


def test_determinism_requires_two_runs():
    base = _scenario()
    explicit = build_assertion(assertion_id="det", category="DETERMINISM", description="det")
    scenario = type(base)(**{**base.__dict__, "assertions": (explicit,)})
    assert EvaluationAssertionEngine().evaluate(scenario, _execution()).outcome == "FAIL"


def test_audience_format_assertion_uses_final_output_metadata():
    base = _scenario("star_copay_customer_format")
    assertion = build_assertion(assertion_id="aud", category="AUDIENCE_FORMAT", description="aud", expected_values=("CUSTOMER", "STANDARD"))
    scenario = type(base)(**{**base.__dict__, "assertions": (assertion,)})
    assert EvaluationAssertionEngine().evaluate(scenario, _execution("star_copay_customer_format")).outcome == "PASS"


@pytest.mark.parametrize("category,field", [
    ("EVIDENCE_FIDELITY", "evidence_fidelity"),
    ("LIMITATION_FIDELITY", "limitation_fidelity"),
    ("CLARIFICATION_FIDELITY", "clarification_fidelity"),
])
def test_fidelity_assertions_use_explicit_final_output_markers(category, field):
    base = _scenario()
    assertion = build_assertion(assertion_id="fid", category=category, description="fid")
    scenario = type(base)(**{**base.__dict__, "assertions": (assertion,)})
    def factory(fixture):
        values = {field: True}
        return _Output("ANSWER", (_Trace("RESPONSE_COMPLETED"),), **values)
    assert EvaluationAssertionEngine().evaluate(scenario, _execution(final_factory=factory)).outcome == "PASS"


def test_optional_failed_assertion_is_still_explicitly_failed_by_contract():
    base = _scenario()
    assertion = build_assertion(assertion_id="optional", category="REQUIRED_BEHAVIOR", description="optional", required=False, expected_values=("missing",))
    scenario = type(base)(**{**base.__dict__, "assertions": (assertion,)})
    result = EvaluationAssertionEngine().evaluate(scenario, _execution())
    assert result.outcome == "FAIL"
    assert result.failed_assertion_ids == ("optional",)


def test_evaluate_all_is_deterministically_ordered():
    scenarios = (_scenario("star_copay_customer_format"), _scenario())
    executions = (_execution("star_copay_customer_format", behaviors=("customer_plain_language", "preserve_evidence")), _execution(behaviors=("preserve_percentage", "preserve_condition", "preserve_evidence")))
    results = EvaluationAssertionEngine().evaluate_all(scenarios, executions)
    assert [item.scenario_id for item in results] == sorted(item.scenario_id for item in scenarios)


def test_evaluate_all_rejects_identity_set_mismatch():
    with pytest.raises(EvaluationAssertionError, match="match exactly"):
        EvaluationAssertionEngine().evaluate_all((_scenario(),), (_execution("star_copay_customer_format"),))


def test_results_are_immutable():
    result = EvaluationAssertionEngine().evaluate(_scenario(), _execution(behaviors=("preserve_percentage", "preserve_condition", "preserve_evidence")))
    with pytest.raises(FrozenInstanceError):
        result.outcome = "FAIL"  # type: ignore[misc]


def test_engine_does_not_modify_execution_or_stage_outputs():
    execution = _execution(behaviors=("preserve_percentage", "preserve_condition", "preserve_evidence"))
    before = execution.runs[0].final_output
    EvaluationAssertionEngine().evaluate(_scenario(), execution)
    assert execution.runs[0].final_output is before


def test_assertion_results_are_explicit_not_opaque():
    result = EvaluationAssertionEngine().evaluate(_scenario(), _execution(behaviors=("preserve_percentage", "preserve_condition", "preserve_evidence")))
    assert result.assertion_results
    assert all(item.message for item in result.assertion_results)
    assert all(item.category for item in result.assertion_results)
