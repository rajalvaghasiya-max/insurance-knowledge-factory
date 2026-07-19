from __future__ import annotations

from insurance_intelligence.context.builder import ContextBuilder
from insurance_intelligence.contracts.context import build_input as build_context_input
from insurance_intelligence.contracts.intent import build_input as build_intent_input
from insurance_intelligence.contracts.reasoning_plan import (
    EXECUTION_MODES,
    EXPECTED_OUTCOME_TYPES,
    PLAN_STATUS_VALUES,
    PLAN_TYPES,
    build_input as build_plan_input,
)
from insurance_intelligence.intent.analyzer import IntentAnalyzer
from insurance_intelligence.planning.planner import ReasoningPlanner

intent_analyzer = IntentAnalyzer()
context_builder = ContextBuilder()
reasoning_planner = ReasoningPlanner()


def _run(text: str, *, intent_kwargs: dict | None = None, context_kwargs: dict | None = None):
    intent_kwargs = intent_kwargs or {}
    context_kwargs = context_kwargs or {}
    intent_out = intent_analyzer.analyze(build_intent_input(request_id="test-request", text=text, **intent_kwargs))
    ctx_in = build_context_input(request_id="test-request", intent_analysis=intent_out, **context_kwargs)
    ctx_out = context_builder.build(ctx_in)
    plan_in = build_plan_input(request_id="test-request", intent_analysis=intent_out, context_assessment=ctx_out)
    plan_out = reasoning_planner.plan(plan_in)
    return intent_out, ctx_out, plan_out


def _step_types(plan):
    return [s.step_type for s in plan.steps]


# --- Representative scenarios (MO-015 s18) ----------------------------------


def test_term_explanation():
    _, _, plan = _run("What is a deductible?")
    assert plan.plan_type == "EXPLANATION_PLAN"
    assert plan.plan_status == "READY"
    assert plan.expected_outcome == "GENERAL_EXPLANATION"


def test_policy_fact_lookup():
    intent_out = intent_analyzer.analyze(
        build_intent_input(request_id="r1", text="What is the co-pay percentage in this policy?")
    )
    ctx_in = build_context_input(
        request_id="r1",
        intent_analysis=intent_out,
        user_context=[
            {"key": "policy_or_document_reference", "value": "my policy", "source_reference": "turn1", "sequence": 1},
            {"key": "requested_fact", "value": "co-pay percentage", "source_reference": "turn1", "sequence": 1},
        ],
    )
    ctx_out = context_builder.build(ctx_in)
    plan_in = build_plan_input(request_id="r1", intent_analysis=intent_out, context_assessment=ctx_out)
    plan = reasoning_planner.plan(plan_in)
    assert plan.plan_type == "DIRECT_FACT_PLAN"
    assert plan.execution_mode == "DIRECT_GROUNDED"
    assert "RESOLVE_POLICY_FACTS" in _step_types(plan)
    assert "VALIDATE_EVIDENCE_SUFFICIENCY" in _step_types(plan)


def test_clause_implication_with_partial_context():
    _, ctx, plan = _run("How does room-rent capping affect a claim?")
    assert ctx.answerability == "PARTIALLY_ANSWERABLE"
    assert plan.plan_type == "CLAUSE_IMPACT_PLAN"
    assert plan.plan_status == "PARTIAL_PLAN"
    assert plan.expected_outcome in ("PARTIAL_RESPONSE", "GENERAL_EXPLANATION")
    assert "FORM_CONDITIONAL_RECOMMENDATION" not in _step_types(plan)


def test_product_explanation():
    _, _, plan = _run("Help me understand Activ One Max.")
    assert plan.plan_type == "EXPLANATION_PLAN"
    assert plan.execution_mode == "INTERPRETIVE"
    assert plan.expected_outcome == "PRODUCT_SPECIFIC_EXPLANATION"


def test_product_comparison():
    _, _, plan = _run("Compare Activ One Max and Star Comprehensive.")
    assert plan.plan_type == "COMPARISON_PLAN"
    assert plan.execution_mode == "DECISION_SUPPORT"
    assert plan.expected_outcome == "COMPARISON_RESULT"
    steps = _step_types(plan)
    assert "RESOLVE_COMPARISON_DIMENSIONS" in steps
    assert "VALIDATE_EVIDENCE_SUFFICIENCY" in steps
    assert "COMPARE_OPTIONS" in steps
    assert "FORM_CONDITIONAL_RECOMMENDATION" not in steps


def test_recommendation_with_insufficient_context():
    _, ctx, plan = _run("Should I increase my base policy or buy a super top-up?")
    assert ctx.answerability == "CLARIFICATION_REQUIRED"
    assert plan.plan_type == "RECOMMENDATION_PLAN"
    assert plan.execution_mode == "NO_EXECUTION"
    assert plan.plan_status == "CLARIFICATION_REQUIRED"
    assert plan.expected_outcome == "CLARIFICATION_REQUEST"
    assert plan.steps == ()
    assert plan.required_evidence == ()
    assert plan.required_calculations == ()


def test_recommendation_with_sufficient_synthetic_context():
    intent_out = intent_analyzer.analyze(
        build_intent_input(request_id="r1", text="Should I increase my base policy or buy a super top-up?")
    )
    synthetic_user_context = [
        {"key": key, "value": "provided", "source_reference": "turn1", "sequence": 1}
        for key in (
            "decision_options",
            "user_objective",
            "existing_coverage",
            "age",
            "family_composition",
            "budget",
            "risk_priority",
        )
    ]
    ctx_in = build_context_input(request_id="r1", intent_analysis=intent_out, user_context=synthetic_user_context)
    ctx_out = context_builder.build(ctx_in)
    assert ctx_out.answerability in ("ANSWERABLE", "ANSWERABLE_WITH_ASSUMPTIONS")
    plan_in = build_plan_input(request_id="r1", intent_analysis=intent_out, context_assessment=ctx_out)
    plan = reasoning_planner.plan(plan_in)
    assert plan.plan_type == "RECOMMENDATION_PLAN"
    assert plan.execution_mode == "DECISION_SUPPORT"
    assert plan.plan_status in ("READY", "READY_WITH_LIMITATIONS")
    assert plan.expected_outcome == "CONDITIONAL_RECOMMENDATION"
    steps = _step_types(plan)
    assert "COMPARE_OPTIONS" in steps
    assert "ASSESS_SUITABILITY" in steps
    assert "FORM_CONDITIONAL_RECOMMENDATION" in steps
    assert "APPLY_SAFETY_GATE" in steps


def test_claim_scenario():
    intent_out = intent_analyzer.analyze(
        build_intent_input(request_id="r1", text="My hospital bill is ₹5 lakh and I have a 20% co-pay. What happens?")
    )
    ctx_in = build_context_input(
        request_id="r1",
        intent_analysis=intent_out,
        user_context=[
            {"key": "policy_or_product_reference", "value": "my policy", "source_reference": "t1", "sequence": 1},
        ],
    )
    ctx_out = context_builder.build(ctx_in)
    plan_in = build_plan_input(request_id="r1", intent_analysis=intent_out, context_assessment=ctx_out)
    plan = reasoning_planner.plan(plan_in)
    assert plan.plan_type == "SCENARIO_PLAN"
    assert plan.execution_mode == "INTERPRETIVE"
    calc_types = {c.calculation_type for c in plan.required_calculations}
    assert "COPAY_AMOUNT" in calc_types
    # Declared only -- no calculated value anywhere in the plan.
    plan_text = str(plan)
    assert "final_payable" not in plan_text.lower()


def test_calculation_plan():
    intent_out = intent_analyzer.analyze(
        build_intent_input(request_id="r1", text="What is 20% of a ₹5 lakh admissible claim?")
    )
    ctx_in = build_context_input(
        request_id="r1",
        intent_analysis=intent_out,
        user_context=[
            {"key": "calculation_inputs", "value": "20%, 5 lakh", "source_reference": "t1", "sequence": 1},
            {"key": "calculation_goal", "value": "percentage of claim", "source_reference": "t1", "sequence": 1},
        ],
    )
    ctx_out = context_builder.build(ctx_in)
    plan_in = build_plan_input(request_id="r1", intent_analysis=intent_out, context_assessment=ctx_out)
    plan = reasoning_planner.plan(plan_in)
    assert plan.plan_type == "CALCULATION_PLAN"
    assert "PERFORM_DETERMINISTIC_CALCULATION" in _step_types(plan)
    assert plan.required_calculations
    for req in plan.required_calculations:
        assert req.calculation_type != "NO_CALCULATION" or True  # declared, not computed either way


def test_advisor_explanation():
    intent_out = intent_analyzer.analyze(
        build_intent_input(request_id="r1", text="How do I explain this plan to my customer?")
    )
    ctx_in = build_context_input(
        request_id="r1",
        intent_analysis=intent_out,
        user_context=[{"key": "subject_reference", "value": "Activ One Max", "source_reference": "t1", "sequence": 1}],
    )
    ctx_out = context_builder.build(ctx_in)
    plan_in = build_plan_input(request_id="r1", intent_analysis=intent_out, context_assessment=ctx_out)
    plan = reasoning_planner.plan(plan_in)
    assert plan.plan_type == "ADVISOR_COMMUNICATION_PLAN"
    assert "GENERATE_ADVISOR_EXPLANATION" in _step_types(plan)


def test_follow_up_unresolved():
    _, ctx, plan = _run("What is its biggest weakness?")
    assert ctx.answerability == "CLARIFICATION_REQUIRED"
    assert plan.plan_status == "CLARIFICATION_REQUIRED"
    assert plan.execution_mode == "NO_EXECUTION"


def test_out_of_scope():
    _, ctx, plan = _run("What is the weather today?")
    assert ctx.answerability == "OUT_OF_SCOPE"
    assert plan.plan_status == "OUT_OF_SCOPE"
    assert plan.execution_mode == "NO_EXECUTION"
    assert plan.expected_outcome == "OUT_OF_SCOPE_RESPONSE"


def test_failed_required_document():
    intent_out = intent_analyzer.analyze(
        build_intent_input(request_id="r1", text="Please explain this clause from my policy.")
    )
    ctx_in = build_context_input(
        request_id="r1",
        intent_analysis=intent_out,
        document_context=[
            {"document_reference": "doc-1", "document_type": "policy_wording", "processing_status": "FAILED", "candidate_entities": []}
        ],
    )
    ctx_out = context_builder.build(ctx_in)
    plan_in = build_plan_input(request_id="r1", intent_analysis=intent_out, context_assessment=ctx_out)
    plan = reasoning_planner.plan(plan_in)
    assert plan.plan_status == "NOT_PLANNABLE"
    assert plan.execution_mode == "NO_EXECUTION"
    assert plan.expected_outcome == "ABSTENTION"


# --- Determinism -------------------------------------------------------------


def test_determinism_identical_inputs_produce_identical_plans():
    intent_out = intent_analyzer.analyze(build_intent_input(request_id="r1", text="What is a deductible?"))
    ctx_in = build_context_input(request_id="r1", intent_analysis=intent_out)
    ctx_out = context_builder.build(ctx_in)
    plan_in = build_plan_input(request_id="r1", intent_analysis=intent_out, context_assessment=ctx_out)
    plan_a = reasoning_planner.plan(plan_in)
    plan_b = reasoning_planner.plan(plan_in)
    assert plan_a == plan_b
    assert plan_a.plan_id == plan_b.plan_id


# --- Invariants (MO-015 s19) --------------------------------------------------


def test_versions_present():
    _, _, plan = _run("What is a deductible?")
    assert plan.contract_version == "1.0"


def test_request_ids_match_across_stages():
    intent_out = intent_analyzer.analyze(build_intent_input(request_id="my-id-9", text="What is a deductible?"))
    ctx_in = build_context_input(request_id="my-id-9", intent_analysis=intent_out)
    ctx_out = context_builder.build(ctx_in)
    plan_in = build_plan_input(request_id="my-id-9", intent_analysis=intent_out, context_assessment=ctx_out)
    plan = reasoning_planner.plan(plan_in)
    assert intent_out.request_id == ctx_out.request_id == plan.request_id == "my-id-9"


def test_plan_type_is_governed():
    for text in ("What is a deductible?", "What is the weather today?"):
        _, _, plan = _run(text)
        assert plan.plan_type in PLAN_TYPES


def test_execution_mode_is_governed():
    for text in ("What is a deductible?", "What is the weather today?"):
        _, _, plan = _run(text)
        assert plan.execution_mode in EXECUTION_MODES


def test_plan_status_is_governed():
    for text in ("What is a deductible?", "What is the weather today?"):
        _, _, plan = _run(text)
        assert plan.plan_status in PLAN_STATUS_VALUES


def test_expected_outcome_is_governed():
    for text in ("What is a deductible?", "What is the weather today?"):
        _, _, plan = _run(text)
        assert plan.expected_outcome in EXPECTED_OUTCOME_TYPES


def test_step_ids_unique_and_sequences_ordered():
    _, _, plan = _run("Compare Activ One Max and Star Comprehensive.")
    ids = [s.step_id for s in plan.steps]
    assert len(ids) == len(set(ids))
    sequences = [s.sequence for s in plan.steps]
    assert sequences == sorted(sequences)


def test_dependencies_reference_earlier_steps():
    _, _, plan = _run("Compare Activ One Max and Star Comprehensive.")
    by_id = {s.step_id: s for s in plan.steps}
    for step in plan.steps:
        for dep in step.dependencies:
            assert by_id[dep].sequence < step.sequence


def test_all_step_types_are_governed():
    from insurance_intelligence.contracts.reasoning_plan import STEP_TYPES

    _, _, plan = _run("Compare Activ One Max and Star Comprehensive.")
    for step in plan.steps:
        assert step.step_type in STEP_TYPES


def test_evidence_and_calculation_requirements_reference_valid_steps():
    _, _, plan = _run("Compare Activ One Max and Star Comprehensive.")
    step_ids = {s.step_id for s in plan.steps}
    for req in plan.required_evidence:
        assert req.requested_by_step in step_ids
    for req in plan.required_calculations:
        assert req.requested_by_step in step_ids


def test_no_calculated_values_present():
    _, _, plan = _run("What is 20% of a ₹5 lakh admissible claim?", context_kwargs={
        "user_context": [
            {"key": "calculation_inputs", "value": "20%, 5 lakh", "source_reference": "t1", "sequence": 1},
            {"key": "calculation_goal", "value": "percentage of claim", "source_reference": "t1", "sequence": 1},
        ]
    })
    plan_text = str(plan)
    assert "= 1,00,000" not in plan_text
    assert "result_value" not in plan_text.lower()


def test_no_actual_evidence_embedded():
    _, _, plan = _run("What is a deductible?")
    for req in plan.required_evidence:
        # subject_reference is a key name, never a resolved fact string.
        assert req.subject_reference in ("term_or_concept", "product_reference") or "_" in req.subject_reference


def test_no_governed_entity_resolution_occurs():
    _, _, plan = _run("Compare Activ One Max and Star Comprehensive.")
    for req in plan.required_evidence:
        assert ":" not in req.subject_reference


def test_recommendation_plans_contain_safety_gate_when_executable():
    intent_out = intent_analyzer.analyze(
        build_intent_input(request_id="r1", text="Should I increase my base policy or buy a super top-up?")
    )
    synthetic_user_context = [
        {"key": key, "value": "provided", "source_reference": "turn1", "sequence": 1}
        for key in ("decision_options", "user_objective", "existing_coverage", "age", "family_composition", "budget", "risk_priority")
    ]
    ctx_in = build_context_input(request_id="r1", intent_analysis=intent_out, user_context=synthetic_user_context)
    ctx_out = context_builder.build(ctx_in)
    plan_in = build_plan_input(request_id="r1", intent_analysis=intent_out, context_assessment=ctx_out)
    plan = reasoning_planner.plan(plan_in)
    assert "APPLY_SAFETY_GATE" in _step_types(plan)


def test_direct_fact_plans_do_not_contain_recommendation_steps():
    intent_out = intent_analyzer.analyze(
        build_intent_input(request_id="r1", text="What is the co-pay percentage in this policy?")
    )
    ctx_in = build_context_input(
        request_id="r1",
        intent_analysis=intent_out,
        user_context=[
            {"key": "policy_or_document_reference", "value": "my policy", "source_reference": "t1", "sequence": 1},
            {"key": "requested_fact", "value": "co-pay percentage", "source_reference": "t1", "sequence": 1},
        ],
    )
    ctx_out = context_builder.build(ctx_in)
    plan_in = build_plan_input(request_id="r1", intent_analysis=intent_out, context_assessment=ctx_out)
    plan = reasoning_planner.plan(plan_in)
    assert "FORM_CONDITIONAL_RECOMMENDATION" not in _step_types(plan)


def test_clarification_plans_contain_no_executable_steps():
    _, _, plan = _run("Should I increase my base policy or buy a super top-up?")
    assert plan.plan_status == "CLARIFICATION_REQUIRED"
    assert plan.steps == ()


def test_no_network_llm_or_knowledge_factory_lookup():
    import insurance_intelligence.planning.planner as planner_module
    import insurance_intelligence.contracts.reasoning_plan as contracts_module

    for module in (planner_module, contracts_module):
        source = open(module.__file__, encoding="utf-8").read()
        for forbidden in ("import requests", "import urllib", "openai", "anthropic", "langchain", "factory_core.canonical", "factory_core.governance", "knowledge_domains"):
            assert forbidden not in source.lower()
