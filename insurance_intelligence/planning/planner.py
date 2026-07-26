"""Deterministic Reasoning Planner (MO-015 v0.1).

Transforms validated Intent Analyzer + Context Builder output into an
explicit, validated execution plan. Declares what must be done; does
not retrieve evidence, calculate, interpret clauses, compare
products, assess suitability, recommend, or generate answers.
"""
from __future__ import annotations

import hashlib

from insurance_intelligence.contracts.reasoning_plan import (
    ReasoningPlan,
    ReasoningPlannerInput,
    build_calculation_requirement,
    build_evidence_requirement,
    build_plan,
    build_plan_step,
    build_stop_condition,
)
from insurance_intelligence.planning.registry import (
    DEFAULT_STEPS_BY_PLAN_TYPE,
    INTENT_TO_CAPABILITY,
    INTENT_TO_PLAN_TYPE,
    PLAN_TYPE_TO_EXECUTION_MODE,
    PLAN_TYPE_TO_EXPECTED_OUTCOME,
    PRODUCT_EXPLANATION_OUTCOME,
)
from insurance_intelligence.planning.validator import validate_plan

_ANSWERABILITY_TO_PLAN_STATUS = {
    "ANSWERABLE": "READY",
    "ANSWERABLE_WITH_ASSUMPTIONS": "READY_WITH_LIMITATIONS",
    "PARTIALLY_ANSWERABLE": "PARTIAL_PLAN",
    "CLARIFICATION_REQUIRED": "CLARIFICATION_REQUIRED",
    "NOT_ANSWERABLE": "NOT_PLANNABLE",
    "OUT_OF_SCOPE": "OUT_OF_SCOPE",
}

_NO_EXECUTION_STATUSES = {"CLARIFICATION_REQUIRED", "NOT_PLANNABLE", "OUT_OF_SCOPE", "INVALID_INPUT"}

_STATUS_TO_FALLBACK_OUTCOME = {
    "CLARIFICATION_REQUIRED": "CLARIFICATION_REQUEST",
    "NOT_PLANNABLE": "ABSTENTION",
    "OUT_OF_SCOPE": "OUT_OF_SCOPE_RESPONSE",
    "INVALID_INPUT": "ABSTENTION",
}


class ReasoningPlanner:
    """Stateless deterministic planner. No I/O, no LLM call."""

    def plan(self, request: ReasoningPlannerInput) -> ReasoningPlan:
        intent_analysis = request.intent_analysis
        context = request.context_assessment
        intent = intent_analysis.primary_intent

        plan_type = INTENT_TO_PLAN_TYPE[intent]
        template_execution_mode = PLAN_TYPE_TO_EXECUTION_MODE[plan_type]
        plan_status = _ANSWERABILITY_TO_PLAN_STATUS[context.answerability]

        classification_basis = ["intent_plan_mapping", "context_answerability"]

        stop_conditions = list(_stop_conditions_from_context(context))

        if plan_status in _NO_EXECUTION_STATUSES:
            expected_outcome = _STATUS_TO_FALLBACK_OUTCOME[plan_status]
            classification_basis.append("active_stop_condition")
            plan = build_plan(
                request_id=request.request_id,
                plan_id=_deterministic_plan_id(request.request_id, plan_type, plan_status, ()),
                plan_type=plan_type,
                execution_mode="NO_EXECUTION",
                goal=_goal_for(intent, intent_analysis.requested_outcome),
                expected_outcome=expected_outcome,
                plan_status=plan_status,
                confidence=_confidence(intent_analysis, context, plan_status, ()),
                steps=(),
                required_evidence=(),
                required_calculations=(),
                required_capabilities=(),
                inherited_assumptions=tuple(f"{a.key}={a.value}" for a in context.assumptions),
                inherited_conflicts=tuple(c.key for c in context.conflicts),
                limitations=tuple(m.key for m in context.missing_required_context),
                stop_conditions=tuple(stop_conditions),
                classification_basis=tuple(classification_basis),
            )
            validate_plan(plan)
            return plan

        # READY / READY_WITH_LIMITATIONS / PARTIAL_PLAN -- build the real plan.
        template_step_types = DEFAULT_STEPS_BY_PLAN_TYPE[plan_type]
        classification_basis.append("selected_template")

        if plan_status == "PARTIAL_PLAN":
            classification_basis.append("partial_context_rule")

        steps = _build_steps(template_step_types)
        step_by_type = {s.step_type: s for s in steps}

        required_evidence = _build_evidence_requirements(plan_type, intent, step_by_type)
        required_calculations = _build_calculation_requirements(plan_type, intent, context, step_by_type)

        required_capabilities = tuple(
            cap for cap in (INTENT_TO_CAPABILITY.get(intent),) if cap is not None
        )
        if required_capabilities:
            classification_basis.append("domain_capability_mapping")

        expected_outcome = PLAN_TYPE_TO_EXPECTED_OUTCOME[plan_type]
        if intent == "PRODUCT_EXPLANATION":
            expected_outcome = PRODUCT_EXPLANATION_OUTCOME
        if plan_status == "PARTIAL_PLAN":
            expected_outcome = "PARTIAL_RESPONSE" if intent != "CLAUSE_IMPLICATION" else "GENERAL_EXPLANATION"

        inherited_assumptions = tuple(f"{a.key}={a.value}" for a in context.assumptions)
        inherited_conflicts = tuple(c.key for c in context.conflicts)
        if inherited_assumptions:
            classification_basis.append("inherited_assumption")
        if inherited_conflicts:
            classification_basis.append("inherited_conflict")
        classification_basis.append("execution_mode_rule")

        limitations = tuple(m.key for m in context.missing_optional_context)

        plan = build_plan(
            request_id=request.request_id,
            plan_id=_deterministic_plan_id(request.request_id, plan_type, plan_status, template_step_types),
            plan_type=plan_type,
            execution_mode=template_execution_mode,
            goal=_goal_for(intent, intent_analysis.requested_outcome),
            expected_outcome=expected_outcome,
            plan_status=plan_status,
            confidence=_confidence(intent_analysis, context, plan_status, steps),
            steps=steps,
            required_evidence=required_evidence,
            required_calculations=required_calculations,
            required_capabilities=required_capabilities,
            inherited_assumptions=inherited_assumptions,
            inherited_conflicts=inherited_conflicts,
            limitations=limitations,
            stop_conditions=tuple(stop_conditions),
            classification_basis=tuple(dict.fromkeys(classification_basis)),
        )
        validate_plan(plan)
        return plan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _goal_for(intent: str, requested_outcome: str) -> str:
    return f"Address a {intent} request: {requested_outcome}"[:500]


def _build_steps(step_types: tuple[str, ...]):
    steps = []
    for index, step_type in enumerate(step_types, start=1):
        dependencies = (f"step-{index - 1}",) if index > 1 else ()
        steps.append(
            build_plan_step(
                step_id=f"step-{index}",
                step_type=step_type,
                sequence=index,
                dependencies=dependencies,
            )
        )
    return tuple(steps)


def _build_evidence_requirements(plan_type: str, intent: str, step_by_type: dict):
    requirements = []
    counter = 1

    def add(category, subject, step_type, *, required=True, authority="AUTHORITATIVE", version="CURRENT_APPLICABLE", reason=""):
        nonlocal counter
        step = step_by_type.get(step_type)
        if step is None:
            return
        requirements.append(
            build_evidence_requirement(
                requirement_id=f"evreq-{counter}",
                evidence_category=category,
                subject_reference=subject,
                required=required,
                authority_requirement=authority,
                version_requirement=version,
                reason=reason or f"Required to complete {step_type}.",
                requested_by_step=step.step_id,
            )
        )
        counter += 1

    if plan_type == "DIRECT_FACT_PLAN":
        add("POLICY_WORDING", "policy_or_product_reference", "RESOLVE_POLICY_FACTS")
        add("POLICY_SCHEDULE", "policy_or_product_reference", "RESOLVE_POLICY_FACTS", required=False)
        add("NORMALIZED_POLICY_FACT", "requested_fact", "RESOLVE_POLICY_FACTS")
    elif plan_type == "EXPLANATION_PLAN":
        category = "NORMALIZED_PRODUCT_FACT" if intent == "PRODUCT_EXPLANATION" else "CLAUSE_TEXT"
        add(category, "term_or_concept" if intent != "PRODUCT_EXPLANATION" else "product_reference", "RESOLVE_CLAUSE_EVIDENCE",
            authority="ANY_GOVERNED" if intent != "PRODUCT_EXPLANATION" else "AUTHORITATIVE")
    elif plan_type == "CLAUSE_IMPACT_PLAN":
        add("CLAUSE_TEXT", "clause_or_feature", "RESOLVE_CLAUSE_EVIDENCE")
    elif plan_type == "DOCUMENT_INTERPRETATION_PLAN":
        add("USER_DOCUMENT", "document_reference", "RESOLVE_DOCUMENT_REFERENCES")
        add("CLAUSE_TEXT", "document_subject", "RESOLVE_CLAUSE_EVIDENCE")
    elif plan_type == "COMPARISON_PLAN":
        add("NORMALIZED_PRODUCT_FACT", "comparison_subject_1", "RESOLVE_PRODUCT_FACTS")
        add("NORMALIZED_PRODUCT_FACT", "comparison_subject_2", "RESOLVE_PRODUCT_FACTS")
    elif plan_type == "SCENARIO_PLAN":
        add("POLICY_WORDING", "policy_or_product_reference", "RESOLVE_CLAIM_CONDITIONS")
        add("POLICY_SCHEDULE", "policy_or_product_reference", "RESOLVE_CLAIM_CONDITIONS", required=False)
        add("CLAUSE_TEXT", "claim_scenario", "RESOLVE_CLAIM_CONDITIONS")
        add("NORMALIZED_POLICY_FACT", "claim_scenario", "RESOLVE_CLAIM_CONDITIONS")
    elif plan_type == "SUITABILITY_PLAN":
        add("NORMALIZED_PRODUCT_FACT", "subject_reference", "RESOLVE_PRODUCT_FACTS")
    elif plan_type == "RECOMMENDATION_PLAN":
        add("NORMALIZED_POLICY_FACT", "existing_coverage", "RESOLVE_POLICY_FACTS")
        add("NORMALIZED_PRODUCT_FACT", "decision_options", "RESOLVE_PRODUCT_FACTS")
    elif plan_type == "ADVISOR_COMMUNICATION_PLAN":
        add("NORMALIZED_PRODUCT_FACT", "subject_reference", "RESOLVE_PRODUCT_FACTS")

    return tuple(requirements)


def _build_calculation_requirements(plan_type: str, intent: str, context, step_by_type: dict):
    if plan_type not in ("SCENARIO_PLAN", "CALCULATION_PLAN", "RECOMMENDATION_PLAN"):
        return ()

    step = step_by_type.get("PERFORM_DETERMINISTIC_CALCULATION")
    if step is None:
        return ()

    resolved_keys = {item.key for item in context.resolved_context}

    if plan_type == "SCENARIO_PLAN":
        if "copay" in resolved_keys or "claim_amount" in resolved_keys:
            calc_type = "COPAY_AMOUNT"
            inputs = tuple(k for k in ("claim_amount", "copay", "deductible") if k in resolved_keys)
        else:
            calc_type = "NO_CALCULATION"
            inputs = ()
    elif plan_type == "CALCULATION_PLAN":
        calc_type = "PERCENTAGE_AMOUNT"
        inputs = ("calculation_inputs",)
    else:  # RECOMMENDATION_PLAN
        calc_type = "PREMIUM_DIFFERENCE"
        inputs = ("existing_coverage", "budget")

    return (
        build_calculation_requirement(
            calculation_id="calcreq-1",
            calculation_type=calc_type,
            required_inputs=inputs,
            required=calc_type != "NO_CALCULATION",
            reason=f"Declared for {plan_type}; not performed by the planner.",
            requested_by_step=step.step_id,
        ),
    )


def _stop_conditions_from_context(context):
    conditions = []
    for missing in context.missing_required_context:
        conditions.append(
            build_stop_condition(
                condition_type="MISSING_REQUIRED_CONTEXT",
                description=missing.reason,
                blocking=True,
                source_stage="CONTEXT_BUILDER",
                required_resolution=missing.clarification_question,
                related_keys=(missing.key,),
            )
        )
    for conflict in context.conflicts:
        if conflict.resolution_status == "UNRESOLVED":
            conditions.append(
                build_stop_condition(
                    condition_type="UNRESOLVED_CONTEXT_CONFLICT",
                    description=f"Conflicting values for {conflict.key}.",
                    blocking=True,
                    source_stage="CONTEXT_BUILDER",
                    required_resolution=f"Confirm the correct value for {conflict.key}.",
                    related_keys=(conflict.key,),
                )
            )
    if context.answerability == "NOT_ANSWERABLE":
        conditions.append(
            build_stop_condition(
                condition_type="REQUIRED_DOCUMENT_FAILED",
                description="A required document failed processing.",
                blocking=True,
                source_stage="CONTEXT_BUILDER",
                required_resolution="Re-upload or reprocess the required document.",
            )
        )
    if context.answerability == "OUT_OF_SCOPE":
        conditions.append(
            build_stop_condition(
                condition_type="OUT_OF_SCOPE_REQUEST",
                description="The request is out of scope for the Insurance Intelligence Layer.",
                blocking=True,
                source_stage="INTENT_ANALYZER",
                required_resolution="N/A",
            )
        )
    # Prospective, not-yet-evaluated future checks.
    conditions.append(
        build_stop_condition(
            condition_type="REQUIRED_EVIDENCE_MISSING",
            description="Evidence resolution has not yet run; this check will be evaluated by the Evidence Resolver.",
            blocking=False,
            source_stage="EVIDENCE_RESOLVER",
            required_resolution="N/A -- prospective check.",
            lifecycle="PLANNED_FUTURE_CHECK",
        )
    )
    return tuple(conditions)


def _confidence(intent_analysis, context, plan_status: str, steps) -> float:
    if plan_status in _NO_EXECUTION_STATUSES:
        return 0.2
    base = 0.5 * intent_analysis.confidence + 0.5 * context.context_completeness
    if plan_status == "READY_WITH_LIMITATIONS":
        base -= 0.1
    elif plan_status == "PARTIAL_PLAN":
        base -= 0.2
    return max(0.0, min(1.0, base))


def _deterministic_plan_id(request_id: str, plan_type: str, plan_status: str, step_types) -> str:
    payload = "|".join([request_id, plan_type, plan_status, ",".join(step_types)])
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"plan_{digest}"
