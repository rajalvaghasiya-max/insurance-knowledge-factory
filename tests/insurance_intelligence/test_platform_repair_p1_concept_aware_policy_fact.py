from __future__ import annotations

from insurance_intelligence.context.builder import ContextBuilder
from insurance_intelligence.contracts.context import (
    build_input as build_context_input,
    build_resolved_context_item,
)
from insurance_intelligence.contracts.full_cycle import build_orchestration_request, build_product_scope
from insurance_intelligence.contracts.intent import build_input as build_intent_input
from insurance_intelligence.intent.analyzer import IntentAnalyzer
from insurance_intelligence.orchestration.real_response_prefix import _scope_session_context
from insurance_intelligence.terminology.concept_resolver import CanonicalConceptResolver
from insurance_intelligence.terminology.health_seed import build_health_concept_registry_v1


def _analyzer() -> IntentAnalyzer:
    return IntentAnalyzer(
        concept_resolver=CanonicalConceptResolver(build_health_concept_registry_v1())
    )


def test_bariatric_conditions_question_reuses_policy_fact_lookup():
    output = _analyzer().analyze(
        build_intent_input(
            request_id="p1-bariatric",
            text="What conditions must I meet for bariatric surgery under Star Comprehensive?",
            domain_hint="health",
        )
    )

    assert output.primary_intent == "POLICY_FACT_LOOKUP"
    assert output.analysis_status == "CLASSIFIED"
    assert "question_pattern" in output.classification_basis
    assert any(
        item.entity_type == "CLAIM_CONCEPT"
        and item.normalized_text == "bariatric_surgery"
        and item.source == "governed_concept_registry"
        for item in output.candidate_entities
    )


def test_stronger_coverage_intent_keeps_precedence_over_policy_fact_fallback():
    output = _analyzer().analyze(
        build_intent_input(
            request_id="p1-coverage-precedence",
            text="Does Star Comprehensive cover bariatric surgery?",
            domain_hint="health",
        )
    )

    assert output.primary_intent == "COVERAGE_CHECK"


def test_room_rent_natural_questions_route_without_concept_specific_runtime_rules():
    questions = (
        "What room am I eligible for in Star Comprehensive?",
        "Does Star Comprehensive have a room rent limit?",
        "What happens if I choose a room above the permitted category?",
        "If I take a deluxe room, will my whole claim be reduced?",
    )

    for index, question in enumerate(questions, start=1):
        output = _analyzer().analyze(
            build_intent_input(
                request_id=f"p1-room-{index}",
                text=question,
                domain_hint="health",
            )
        )

        assert output.primary_intent == "POLICY_FACT_LOOKUP", question
        assert output.analysis_status == "CLASSIFIED", question
        assert any(
            item.entity_type == "CLAIM_CONCEPT"
            and item.normalized_text == "room_rent_limit"
            and item.source == "governed_concept_registry"
            for item in output.candidate_entities
        ), question


def test_policy_fact_context_uses_governed_concept_and_bound_product_reference():
    intent = _analyzer().analyze(
        build_intent_input(
            request_id="p1-context",
            text="What room am I eligible for in Star Comprehensive?",
            domain_hint="health",
        )
    )
    session_context = (
        build_resolved_context_item(
            key="policy_or_document_reference",
            value="star_health:star_comprehensive",
            category="POLICY",
            provenance="SYSTEM_DERIVED",
            source_reference="orchestration.product_scope.candidate",
            confidence=1.0,
            materiality="high",
        ),
    )

    context = ContextBuilder().build(
        build_context_input(
            request_id="p1-context",
            intent_analysis=intent,
            session_context=session_context,
        )
    )

    assert context.answerability == "ANSWERABLE"
    resolved = {item.key: item.value for item in context.resolved_context if item.status == "ACTIVE"}
    assert resolved["requested_fact"] == "room_rent_limit"
    assert resolved["policy_or_document_reference"] == "star_health:star_comprehensive"


def test_orchestration_product_scope_supplies_policy_fact_reference_context():
    request = build_orchestration_request(
        execution_id="p1-scope",
        mode="INTELLIGENCE_RESPONSE",
        product_scope=build_product_scope(
            domain="health",
            insurer_id="star_health",
            product_id="star_comprehensive",
        ),
        question="What room am I eligible for in Star Comprehensive?",
        audience="CUSTOMER",
        knowledge_snapshot_id="p1-snapshot",
        allow_llm_rendering=False,
    )
    intent = _analyzer().analyze(
        build_intent_input(
            request_id="p1-scope",
            text=request.question or "",
            domain_hint="health",
        )
    )

    context = _scope_session_context(request, intent)

    assert tuple((item.key, item.value) for item in context) == (
        ("policy_or_document_reference", "star_health:star_comprehensive"),
    )
