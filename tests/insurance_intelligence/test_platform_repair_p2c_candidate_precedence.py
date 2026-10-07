from __future__ import annotations

from insurance_intelligence.context.builder import ContextBuilder
from insurance_intelligence.contracts.context import (
    build_input as build_context_input,
    build_resolved_context_item,
)
from insurance_intelligence.contracts.intent import (
    build_candidate_entity,
    build_input as build_intent_input,
    build_output as build_intent_output,
)
from insurance_intelligence.intent.analyzer import IntentAnalyzer
from insurance_intelligence.terminology.concept_resolver import CanonicalConceptResolver
from insurance_intelligence.terminology.health_seed import build_health_concept_registry_v1


def _product_context():
    return (
        build_resolved_context_item(
            key="policy_or_document_reference",
            value="star_health:star_comprehensive",
            category="POLICY",
            provenance="SYSTEM_DERIVED",
            source_reference="test.product_scope",
            confidence=1.0,
            materiality="high",
        ),
    )


def test_governed_room_rent_candidate_beats_generic_claim_candidate_for_requested_fact():
    intent = IntentAnalyzer(
        concept_resolver=CanonicalConceptResolver(build_health_concept_registry_v1())
    ).analyze(
        build_intent_input(
            request_id="p2c-room-q4",
            text="If I take a deluxe room, will my whole claim be reduced?",
            domain_hint="health",
        )
    )

    assert intent.primary_intent == "POLICY_FACT_LOOKUP"
    claim_candidates = tuple(
        item for item in intent.candidate_entities if item.entity_type == "CLAIM_CONCEPT"
    )
    assert {item.normalized_text for item in claim_candidates} >= {"claim", "room_rent_limit"}

    context = ContextBuilder().build(
        build_context_input(
            request_id="p2c-room-q4",
            intent_analysis=intent,
            session_context=_product_context(),
        )
    )

    resolved = {
        item.key: item.value
        for item in context.resolved_context
        if item.status == "ACTIVE"
    }
    assert context.answerability == "ANSWERABLE"
    assert resolved["requested_fact"] == "room_rent_limit"


def test_equal_confidence_disagreement_fails_closed_instead_of_using_input_order():
    intent = build_intent_output(
        request_id="p2c-tie",
        primary_intent="POLICY_FACT_LOOKUP",
        domain="health",
        requested_outcome="What is the relevant fact?",
        confidence=0.8,
        analysis_status="CLASSIFIED",
        candidate_entities=(
            build_candidate_entity(
                entity_type="CLAIM_CONCEPT",
                surface_text="first",
                normalized_text="first_fact",
                source="candidate_a",
                confidence=0.8,
            ),
            build_candidate_entity(
                entity_type="CLAIM_CONCEPT",
                surface_text="second",
                normalized_text="second_fact",
                source="candidate_b",
                confidence=0.8,
            ),
        ),
        classification_basis=("matched_term",),
    )

    context = ContextBuilder().build(
        build_context_input(
            request_id="p2c-tie",
            intent_analysis=intent,
            session_context=_product_context(),
        )
    )

    assert context.answerability == "CLARIFICATION_REQUIRED"
    assert "requested_fact" not in {
        item.key for item in context.resolved_context if item.status == "ACTIVE"
    }
    assert tuple(item.key for item in context.missing_required_context) == ("requested_fact",)
