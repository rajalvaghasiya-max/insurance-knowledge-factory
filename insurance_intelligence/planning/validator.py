"""Deterministic Reasoning Plan validator (MO-015).

Separate from the planner itself: rejects governed-but-inconsistent
plans (e.g. a plan type paired with an execution mode it does not
support, or a recommendation plan lacking its required safety gate).
"""
from __future__ import annotations

from insurance_intelligence.contracts.reasoning_plan import ReasoningPlan
from insurance_intelligence.planning.registry import (
    PLAN_TYPE_TO_EXECUTION_MODE,
    RECOMMENDATION_REQUIRED_STEP,
    SAFETY_GATE_STEP,
    STEP_REGISTRY,
)


class PlanValidationError(ValueError):
    pass


def validate_plan(plan: ReasoningPlan) -> None:
    """Raises PlanValidationError on any governance violation. Returns
    None (no result object) when the plan is valid -- mirrors the
    fail-closed style of the Knowledge Factory's generic contracts."""

    if plan.execution_mode != "NO_EXECUTION":
        expected_mode = PLAN_TYPE_TO_EXECUTION_MODE[plan.plan_type]
        if plan.execution_mode != expected_mode:
            raise PlanValidationError(
                f"execution_mode {plan.execution_mode!r} is inconsistent with plan_type {plan.plan_type!r} "
                f"(expected {expected_mode!r})"
            )

    step_ids = {step.step_id for step in plan.steps}
    if len(step_ids) != len(plan.steps):
        raise PlanValidationError("duplicate step_id values")
    sequences = [step.sequence for step in plan.steps]
    if len(set(sequences)) != len(sequences):
        raise PlanValidationError("duplicate step sequence values")

    for step in plan.steps:
        for dependency in step.dependencies:
            if dependency not in step_ids:
                raise PlanValidationError(f"step {step.step_id} depends on missing step {dependency}")
        dep_sequences = [s.sequence for s in plan.steps if s.step_id in step.dependencies]
        if any(dep_seq >= step.sequence for dep_seq in dep_sequences):
            raise PlanValidationError(f"step {step.step_id} has a forward or circular dependency")

        definition = STEP_REGISTRY.get(step.step_type)
        if definition is None:
            raise PlanValidationError(f"step_type {step.step_type!r} is not governed")
        if plan.plan_type not in definition.allowed_plan_types:
            raise PlanValidationError(f"step_type {step.step_type!r} is not allowed for plan_type {plan.plan_type!r}")

    evidence_ids = {req.requirement_id for req in plan.required_evidence}
    for req in plan.required_evidence:
        if req.requested_by_step not in step_ids:
            raise PlanValidationError(f"evidence requirement {req.requirement_id} references unknown step {req.requested_by_step}")
    calculation_ids = {req.calculation_id for req in plan.required_calculations}
    for req in plan.required_calculations:
        if req.requested_by_step not in step_ids:
            raise PlanValidationError(f"calculation requirement {req.calculation_id} references unknown step {req.requested_by_step}")
    if len(evidence_ids) != len(plan.required_evidence):
        raise PlanValidationError("duplicate evidence requirement_id values")
    if len(calculation_ids) != len(plan.required_calculations):
        raise PlanValidationError("duplicate calculation_id values")

    step_types = {step.step_type for step in plan.steps}

    if plan.plan_type == "RECOMMENDATION_PLAN" and RECOMMENDATION_REQUIRED_STEP in step_types:
        if SAFETY_GATE_STEP not in step_types:
            raise PlanValidationError("a recommendation plan with FORM_CONDITIONAL_RECOMMENDATION must include APPLY_SAFETY_GATE")

    if plan.plan_type == "COMPARISON_PLAN" and "COMPARE_OPTIONS" in step_types:
        if "VALIDATE_EVIDENCE_SUFFICIENCY" not in step_types:
            raise PlanValidationError("a comparison plan performing COMPARE_OPTIONS must include VALIDATE_EVIDENCE_SUFFICIENCY")

    if plan.plan_type == "DIRECT_FACT_PLAN" and RECOMMENDATION_REQUIRED_STEP in step_types:
        raise PlanValidationError("a direct fact plan must not include a recommendation step")

    if plan.plan_status == "CLARIFICATION_REQUIRED":
        executable = step_types & {
            "RESOLVE_POLICY_FACTS", "RESOLVE_PRODUCT_FACTS", "RESOLVE_CLAUSE_EVIDENCE",
            "PERFORM_DETERMINISTIC_CALCULATION", "APPLY_DOMAIN_RULES", "COMPARE_OPTIONS",
            "ASSESS_SUITABILITY", "FORM_CONDITIONAL_RECOMMENDATION",
        }
        if executable:
            raise PlanValidationError("a CLARIFICATION_REQUIRED plan must not contain executable evidence or reasoning steps")

    if plan.execution_mode == "NO_EXECUTION" and plan.steps:
        raise PlanValidationError("a NO_EXECUTION plan must not contain executable processing steps")
