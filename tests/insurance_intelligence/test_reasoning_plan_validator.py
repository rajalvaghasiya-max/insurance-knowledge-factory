from __future__ import annotations

import pytest

from insurance_intelligence.contracts.reasoning_plan import build_plan, build_plan_step
from insurance_intelligence.planning.validator import PlanValidationError, validate_plan


def _step(step_id, step_type, sequence, dependencies=()):
    return build_plan_step(step_id=step_id, step_type=step_type, sequence=sequence, dependencies=dependencies)


def test_valid_plan_passes():
    steps = [
        _step("s1", "VALIDATE_REQUEST_CONTEXT", 1),
        _step("s2", "RESOLVE_CLAUSE_EVIDENCE", 2, ("s1",)),
        _step("s3", "VALIDATE_EVIDENCE_SUFFICIENCY", 3, ("s2",)),
        _step("s4", "GENERATE_CONSUMER_EXPLANATION", 4, ("s3",)),
        _step("s5", "ASSEMBLE_EVIDENCE_TRACE", 5, ("s4",)),
        _step("s6", "APPLY_SAFETY_GATE", 6, ("s5",)),
    ]
    plan = build_plan(
        request_id="r1", plan_id="p1", plan_type="EXPLANATION_PLAN", execution_mode="INTERPRETIVE",
        goal="x", expected_outcome="GENERAL_EXPLANATION", plan_status="READY", confidence=0.8, steps=steps,
    )
    validate_plan(plan)  # must not raise


def test_execution_mode_inconsistent_with_plan_type_rejected():
    plan = build_plan(
        request_id="r1", plan_id="p1", plan_type="EXPLANATION_PLAN", execution_mode="DECISION_SUPPORT",
        goal="x", expected_outcome="GENERAL_EXPLANATION", plan_status="READY", confidence=0.8,
    )
    with pytest.raises(PlanValidationError, match="inconsistent"):
        validate_plan(plan)


def test_step_type_not_allowed_for_plan_type_rejected():
    steps = [_step("s1", "FORM_CONDITIONAL_RECOMMENDATION", 1)]
    plan = build_plan(
        request_id="r1", plan_id="p1", plan_type="DIRECT_FACT_PLAN", execution_mode="DIRECT_GROUNDED",
        goal="x", expected_outcome="DIRECT_FACT_RESPONSE", plan_status="READY", confidence=0.8, steps=steps,
    )
    with pytest.raises(PlanValidationError, match="not allowed"):
        validate_plan(plan)


def test_recommendation_plan_without_safety_gate_rejected():
    steps = [_step("s1", "FORM_CONDITIONAL_RECOMMENDATION", 1)]
    plan = build_plan(
        request_id="r1", plan_id="p1", plan_type="RECOMMENDATION_PLAN", execution_mode="DECISION_SUPPORT",
        goal="x", expected_outcome="CONDITIONAL_RECOMMENDATION", plan_status="READY", confidence=0.8, steps=steps,
    )
    with pytest.raises(PlanValidationError, match="SAFETY_GATE"):
        validate_plan(plan)


def test_comparison_plan_missing_evidence_sufficiency_rejected():
    steps = [_step("s1", "COMPARE_OPTIONS", 1)]
    plan = build_plan(
        request_id="r1", plan_id="p1", plan_type="COMPARISON_PLAN", execution_mode="DECISION_SUPPORT",
        goal="x", expected_outcome="COMPARISON_RESULT", plan_status="READY", confidence=0.8, steps=steps,
    )
    with pytest.raises(PlanValidationError, match="VALIDATE_EVIDENCE_SUFFICIENCY"):
        validate_plan(plan)


def test_clarification_required_plan_with_executable_steps_rejected():
    steps = [_step("s1", "RESOLVE_POLICY_FACTS", 1)]
    plan = build_plan(
        request_id="r1", plan_id="p1", plan_type="DIRECT_FACT_PLAN", execution_mode="DIRECT_GROUNDED",
        goal="x", expected_outcome="CLARIFICATION_REQUEST", plan_status="CLARIFICATION_REQUIRED", confidence=0.2,
        steps=steps,
    )
    with pytest.raises(PlanValidationError, match="CLARIFICATION_REQUIRED"):
        validate_plan(plan)


def test_no_execution_mode_with_steps_rejected():
    steps = [_step("s1", "VALIDATE_REQUEST_CONTEXT", 1)]
    plan = build_plan(
        request_id="r1", plan_id="p1", plan_type="EXPLANATION_PLAN", execution_mode="NO_EXECUTION",
        goal="x", expected_outcome="OUT_OF_SCOPE_RESPONSE", plan_status="OUT_OF_SCOPE", confidence=0.2, steps=steps,
    )
    with pytest.raises(PlanValidationError, match="NO_EXECUTION"):
        validate_plan(plan)


def test_direct_fact_plan_with_recommendation_step_rejected():
    steps = [
        _step("s1", "RESOLVE_POLICY_FACTS", 1),
    ]
    # Attach a recommendation step disallowed even structurally for this plan type.
    plan_steps = steps + [_step("s2", "FORM_CONDITIONAL_RECOMMENDATION", 2, ("s1",))]
    plan = build_plan(
        request_id="r1", plan_id="p1", plan_type="DIRECT_FACT_PLAN", execution_mode="DIRECT_GROUNDED",
        goal="x", expected_outcome="DIRECT_FACT_RESPONSE", plan_status="READY", confidence=0.8, steps=plan_steps,
    )
    with pytest.raises(PlanValidationError):
        validate_plan(plan)
