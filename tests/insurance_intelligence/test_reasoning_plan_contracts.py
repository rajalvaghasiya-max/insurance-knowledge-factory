from __future__ import annotations

import pytest

from insurance_intelligence.contracts.context import build_input as build_context_input
from insurance_intelligence.contracts.intent import build_input as build_intent_input
from insurance_intelligence.contracts.reasoning_plan import (
    ReasoningPlannerError,
    build_evidence_requirement,
    build_input,
    build_plan,
    build_plan_step,
    build_stop_condition,
)
from insurance_intelligence.context.builder import ContextBuilder
from insurance_intelligence.intent.analyzer import IntentAnalyzer

intent_analyzer = IntentAnalyzer()
context_builder = ContextBuilder()


def _sample_context():
    intent_out = intent_analyzer.analyze(build_intent_input(request_id="r1", text="What is a deductible?"))
    ctx_in = build_context_input(request_id="r1", intent_analysis=intent_out)
    return intent_out, context_builder.build(ctx_in)


def test_build_input_defaults():
    intent_out, ctx_out = _sample_context()
    result = build_input(request_id="r1", intent_analysis=intent_out, context_assessment=ctx_out)
    assert result.contract_version == "1.0"
    assert result.domain == "unknown"
    assert result.planning_mode == "AUTO"


def test_build_input_rejects_wrong_contract_version():
    intent_out, ctx_out = _sample_context()
    with pytest.raises(ReasoningPlannerError, match="contract_version"):
        build_input(request_id="r1", intent_analysis=intent_out, context_assessment=ctx_out, contract_version="0.1")


def test_build_input_requires_matching_request_ids():
    intent_out, ctx_out = _sample_context()
    with pytest.raises(ReasoningPlannerError, match="request_id"):
        build_input(request_id="different-id", intent_analysis=intent_out, context_assessment=ctx_out)


def test_build_plan_step_requires_governed_step_type():
    with pytest.raises(ReasoningPlannerError):
        build_plan_step(step_id="s1", step_type="NOT_A_STEP", sequence=1)


def test_build_evidence_requirement_validates_category():
    with pytest.raises(ReasoningPlannerError):
        build_evidence_requirement(
            requirement_id="e1", evidence_category="NOT_A_CATEGORY", subject_reference="x",
            required=True, authority_requirement="AUTHORITATIVE", version_requirement="CURRENT_APPLICABLE",
            reason="x", requested_by_step="s1",
        )


def test_build_stop_condition_validates_type():
    with pytest.raises(ReasoningPlannerError):
        build_stop_condition(
            condition_type="NOT_A_CONDITION", description="x", blocking=True,
            source_stage="CONTEXT_BUILDER", required_resolution="x",
        )


def test_build_plan_requires_governed_plan_type():
    with pytest.raises(ReasoningPlannerError):
        build_plan(
            request_id="r1", plan_id="p1", plan_type="NOT_A_PLAN", execution_mode="DIRECT_GROUNDED",
            goal="x", expected_outcome="GENERAL_EXPLANATION", plan_status="READY", confidence=0.8,
        )


def test_build_plan_rejects_duplicate_step_ids():
    step_a = build_plan_step(step_id="s1", step_type="VALIDATE_REQUEST_CONTEXT", sequence=1)
    step_b = build_plan_step(step_id="s1", step_type="ASSEMBLE_EVIDENCE_TRACE", sequence=2)
    with pytest.raises(ReasoningPlannerError, match="unique"):
        build_plan(
            request_id="r1", plan_id="p1", plan_type="EXPLANATION_PLAN", execution_mode="INTERPRETIVE",
            goal="x", expected_outcome="GENERAL_EXPLANATION", plan_status="READY", confidence=0.8,
            steps=[step_a, step_b],
        )


def test_build_plan_rejects_forward_dependency():
    step_a = build_plan_step(step_id="s1", step_type="VALIDATE_REQUEST_CONTEXT", sequence=1, dependencies=("s2",))
    step_b = build_plan_step(step_id="s2", step_type="ASSEMBLE_EVIDENCE_TRACE", sequence=2)
    with pytest.raises(ReasoningPlannerError, match="precede"):
        build_plan(
            request_id="r1", plan_id="p1", plan_type="EXPLANATION_PLAN", execution_mode="INTERPRETIVE",
            goal="x", expected_outcome="GENERAL_EXPLANATION", plan_status="READY", confidence=0.8,
            steps=[step_a, step_b],
        )


def test_build_plan_rejects_missing_dependency():
    step_a = build_plan_step(step_id="s1", step_type="VALIDATE_REQUEST_CONTEXT", sequence=1, dependencies=("ghost",))
    with pytest.raises(ReasoningPlannerError, match="unknown step"):
        build_plan(
            request_id="r1", plan_id="p1", plan_type="EXPLANATION_PLAN", execution_mode="INTERPRETIVE",
            goal="x", expected_outcome="GENERAL_EXPLANATION", plan_status="READY", confidence=0.8,
            steps=[step_a],
        )


def test_build_plan_rejects_confidence_out_of_bounds():
    with pytest.raises(ReasoningPlannerError, match="confidence"):
        build_plan(
            request_id="r1", plan_id="p1", plan_type="EXPLANATION_PLAN", execution_mode="INTERPRETIVE",
            goal="x", expected_outcome="GENERAL_EXPLANATION", plan_status="READY", confidence=1.2,
        )


def test_build_plan_accepts_valid_minimal_plan():
    plan = build_plan(
        request_id="r1", plan_id="p1", plan_type="EXPLANATION_PLAN", execution_mode="NO_EXECUTION",
        goal="x", expected_outcome="OUT_OF_SCOPE_RESPONSE", plan_status="OUT_OF_SCOPE", confidence=0.2,
    )
    assert plan.steps == ()
