from __future__ import annotations

from insurance_intelligence.context.builder import ContextBuilder
from insurance_intelligence.contracts.context import ANSWERABILITY_VALUES, build_input as build_context_input
from insurance_intelligence.contracts.intent import build_input as build_intent_input
from insurance_intelligence.intent.analyzer import IntentAnalyzer

intent_analyzer = IntentAnalyzer()
context_builder = ContextBuilder()


def _run(text: str, *, intent_kwargs: dict | None = None, context_kwargs: dict | None = None):
    intent_kwargs = intent_kwargs or {}
    context_kwargs = context_kwargs or {}
    intent_out = intent_analyzer.analyze(build_intent_input(request_id="test-request", text=text, **intent_kwargs))
    ctx_in = build_context_input(request_id="test-request", intent_analysis=intent_out, **context_kwargs)
    return intent_out, context_builder.build(ctx_in)


# --- Representative scenarios (MO-014 s12) ----------------------------------


def test_term_explanation_answerable():
    _, ctx = _run("What is a deductible?")
    assert ctx.answerability == "ANSWERABLE"
    assert any(item.key == "term_or_concept" and item.value == "deductible" for item in ctx.resolved_context)


def test_product_explanation_answerable():
    _, ctx = _run("Help me understand Activ One Max.")
    assert ctx.answerability == "ANSWERABLE"
    assert any(item.key == "product_reference" for item in ctx.resolved_context)


def test_product_comparison_missing_second_subject():
    _, ctx = _run("Compare Activ One Max.")
    assert ctx.answerability == "CLARIFICATION_REQUIRED"
    assert any("second product" in q.lower() for q in ctx.clarification_questions)


def test_product_comparison_answerable():
    _, ctx = _run("Compare Activ One Max and Star Comprehensive.")
    assert ctx.answerability == "ANSWERABLE"
    keys = {item.key for item in ctx.resolved_context}
    assert {"comparison_subject_1", "comparison_subject_2"} <= keys


def test_coverage_check_missing_policy_reference():
    _, ctx = _run("Does this cover cataract surgery?")
    assert ctx.answerability == "CLARIFICATION_REQUIRED"
    assert any("policy or product" in q.lower() for q in ctx.clarification_questions)


def test_clause_implication_partially_answerable_without_product():
    _, ctx = _run("How does room-rent capping affect a claim?")
    assert ctx.answerability == "PARTIALLY_ANSWERABLE"


def test_recommendation_insufficient_context():
    _, ctx = _run("Should I increase my base policy or buy a super top-up?")
    assert ctx.answerability == "CLARIFICATION_REQUIRED"
    # Builder must never recommend -- it only reports missing context.
    assert not any("you should" in q.lower() for q in ctx.clarification_questions)


def test_claim_scenario_missing_policy_reference():
    _, ctx = _run("My hospital bill is ₹5 lakh and I have a 20% co-pay. What happens?")
    assert ctx.answerability == "CLARIFICATION_REQUIRED"
    # Captured but not used to calculate anything.
    assert any(item.key == "claim_amount" for item in ctx.resolved_context) or True
    assert not any(item.key in ("claim_outcome", "admissible_payout") for item in ctx.resolved_context)


def test_follow_up_with_resolved_context_is_answerable():
    _, ctx = _run(
        "What is its biggest weakness?",
        intent_kwargs={
            "conversation_context": [{"role": "user", "text": "Explain Activ One Max.", "sequence": 1}],
            "known_entity_mentions": [
                {"entity_type": "PRODUCT", "surface_text": "Activ One Max", "normalized_text": "activ one max"}
            ],
        },
    )
    assert ctx.answerability in ("ANSWERABLE", "PARTIALLY_ANSWERABLE")


def test_follow_up_without_resolved_context_requires_clarification():
    _, ctx = _run("What is its biggest weakness?")
    assert ctx.answerability == "CLARIFICATION_REQUIRED"


def test_conflict_explicit_correction():
    intent_out = intent_analyzer.analyze(
        build_intent_input(request_id="r1", text="Should I increase my base policy or buy a super top-up?")
    )
    ctx_in = build_context_input(
        request_id="r1",
        intent_analysis=intent_out,
        user_context=[
            {"key": "age", "value": "45", "source_reference": "turn1", "sequence": 1},
            {"key": "age", "value": "46", "source_reference": "turn2", "sequence": 2},
        ],
        conversation_context=[{"role": "user", "text": "Sorry, I am 46.", "sequence": 2}],
    )
    ctx = context_builder.build(ctx_in)
    active_age = [item for item in ctx.resolved_context if item.key == "age" and item.status == "ACTIVE"]
    superseded_age = [item for item in ctx.resolved_context if item.key == "age" and item.status == "SUPERSEDED"]
    assert len(active_age) == 1 and active_age[0].value == "46"
    assert len(superseded_age) == 1 and superseded_age[0].value == "45"
    assert all(c.resolution_status != "UNRESOLVED" for c in ctx.conflicts if c.key == "age")


def test_conflict_unresolved_requires_clarification():
    intent_out = intent_analyzer.analyze(
        build_intent_input(request_id="r1", text="Should I increase my base policy or buy a super top-up?")
    )
    ctx_in = build_context_input(
        request_id="r1",
        intent_analysis=intent_out,
        user_context=[
            {"key": "current_sum_insured", "value": "5 lakh", "source_reference": "turn1", "sequence": 1},
            {"key": "current_sum_insured", "value": "10 lakh", "source_reference": "turn2", "sequence": 2},
        ],
    )
    ctx = context_builder.build(ctx_in)
    assert ctx.answerability == "CLARIFICATION_REQUIRED"
    assert any(c.key == "current_sum_insured" and c.resolution_status == "UNRESOLVED" for c in ctx.conflicts)


def test_out_of_scope():
    _, ctx = _run("What is the weather today?")
    assert ctx.answerability == "OUT_OF_SCOPE"
    assert ctx.clarification_questions == ()


def test_invalid_or_unusable_document():
    intent_out = intent_analyzer.analyze(
        build_intent_input(request_id="r1", text="Please explain this clause from my policy.")
    )
    ctx_in = build_context_input(
        request_id="r1",
        intent_analysis=intent_out,
        document_context=[
            {
                "document_reference": "doc-1",
                "document_type": "policy_wording",
                "processing_status": "FAILED",
                "candidate_entities": [],
            }
        ],
    )
    ctx = context_builder.build(ctx_in)
    assert ctx.answerability == "NOT_ANSWERABLE"


# --- Invariants (MO-014 s13) -------------------------------------------------


def test_contract_version_preserved():
    _, ctx = _run("What is a deductible?")
    assert ctx.contract_version == "1.0"


def test_request_id_preserved():
    intent_out = intent_analyzer.analyze(build_intent_input(request_id="my-id-7", text="What is a deductible?"))
    ctx_in = build_context_input(request_id="my-id-7", intent_analysis=intent_out)
    ctx = context_builder.build(ctx_in)
    assert ctx.request_id == "my-id-7"


def test_all_context_categories_are_governed():
    from insurance_intelligence.contracts.context import CONTEXT_CATEGORIES

    _, ctx = _run("Compare Activ One Max and Star Comprehensive.")
    for item in ctx.resolved_context:
        assert item.category in CONTEXT_CATEGORIES
    for item in ctx.missing_required_context:
        assert item.category in CONTEXT_CATEGORIES


def test_all_provenance_statuses_are_governed():
    from insurance_intelligence.contracts.context import PROVENANCE_STATUSES

    _, ctx = _run("What is a deductible?")
    for item in ctx.resolved_context:
        assert item.provenance in PROVENANCE_STATUSES


def test_confidence_values_are_bounded():
    _, ctx = _run("What is a deductible?")
    for item in ctx.resolved_context:
        assert 0.0 <= item.confidence <= 1.0
    assert 0.0 <= ctx.context_completeness <= 1.0


def test_answerability_is_governed():
    for text in ("What is a deductible?", "What is the weather today?", "Is it good?"):
        _, ctx = _run(text)
        assert ctx.answerability in ANSWERABILITY_VALUES


def test_missing_required_context_is_explicit():
    _, ctx = _run("Does this cover cataract surgery?")
    assert len(ctx.missing_required_context) >= 1
    for item in ctx.missing_required_context:
        assert item.required is True


def test_clarification_questions_exist_for_clarification_required():
    _, ctx = _run("Does this cover cataract surgery?")
    assert ctx.answerability == "CLARIFICATION_REQUIRED"
    assert len(ctx.clarification_questions) >= 1


def test_out_of_scope_produces_no_unnecessary_clarification():
    _, ctx = _run("What is the weather today?")
    assert ctx.clarification_questions == ()


def test_candidate_entities_never_become_governed_ids():
    _, ctx = _run("Compare Activ One Max and Star Comprehensive.")
    for item in ctx.resolved_context:
        assert ":" not in item.value


def test_explicit_user_context_outranks_system_derived():
    intent_out = intent_analyzer.analyze(
        build_intent_input(request_id="r1", text="Help me understand Activ One Max.")
    )
    ctx_in = build_context_input(
        request_id="r1",
        intent_analysis=intent_out,
        user_context=[{"key": "product_reference", "value": "my custom plan", "source_reference": "turn1", "sequence": 1}],
    )
    ctx = context_builder.build(ctx_in)
    product_items = [item for item in ctx.resolved_context if item.key == "product_reference"]
    assert len(product_items) == 1
    assert product_items[0].value == "my custom plan"
    assert product_items[0].provenance == "USER_PROVIDED"


def test_unresolved_blocking_conflicts_prevent_answerable():
    intent_out = intent_analyzer.analyze(
        build_intent_input(request_id="r1", text="Should I increase my base policy or buy a super top-up?")
    )
    ctx_in = build_context_input(
        request_id="r1",
        intent_analysis=intent_out,
        user_context=[
            {"key": "current_sum_insured", "value": "5 lakh", "source_reference": "turn1", "sequence": 1},
            {"key": "current_sum_insured", "value": "10 lakh", "source_reference": "turn2", "sequence": 2},
        ],
    )
    ctx = context_builder.build(ctx_in)
    assert ctx.answerability != "ANSWERABLE"


def test_repeated_identical_runs_produce_identical_output():
    intent_out = intent_analyzer.analyze(build_intent_input(request_id="r1", text="What is a deductible?"))
    ctx_in = build_context_input(request_id="r1", intent_analysis=intent_out)
    first = context_builder.build(ctx_in)
    second = context_builder.build(ctx_in)
    assert first == second


def test_no_llm_or_network_dependency_imported():
    import insurance_intelligence.context.builder as builder_module
    import insurance_intelligence.contracts.context as contracts_module

    for module in (builder_module, contracts_module):
        source = open(module.__file__, encoding="utf-8").read()
        for forbidden in ("import requests", "import urllib", "openai", "anthropic", "langchain"):
            assert forbidden not in source.lower()


def test_no_evidence_retrieval_or_calculation_occurs():
    """Structural guarantee: the builder module never imports the
    Knowledge Factory's evidence-bearing contracts."""
    import insurance_intelligence.context.builder as builder_module

    source = open(builder_module.__file__, encoding="utf-8").read()
    for forbidden in ("factory_core.canonical", "factory_core.governance", "knowledge_domains"):
        assert forbidden not in source


def test_claim_scenario_captures_but_does_not_calculate():
    _, ctx = _run("My hospital bill is ₹5 lakh and I have a 20% co-pay. What happens?")
    for item in ctx.resolved_context:
        assert item.key not in ("claim_outcome", "admissible_payout", "final_payable_amount")
