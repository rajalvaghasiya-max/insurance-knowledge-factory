from __future__ import annotations

from insurance_intelligence.context.builder import ContextBuilder
from insurance_intelligence.contracts.context import build_input as build_context_input
from insurance_intelligence.contracts.intent import build_input as build_intent_input
from insurance_intelligence.contracts.reasoning_plan import build_input as build_plan_input
from insurance_intelligence.intent.analyzer import IntentAnalyzer
from insurance_intelligence.orchestration.real_response_prefix import _resolved_context_values
from insurance_intelligence.planning.planner import ReasoningPlanner


def _room_rent_context():
    intent = IntentAnalyzer().analyze(
        build_intent_input(
            request_id="p2b-plan",
            text="What is the room rent limit in this policy?",
            domain_hint="health",
        )
    )
    context = ContextBuilder().build(
        build_context_input(
            request_id="p2b-plan",
            intent_analysis=intent,
            user_context=[
                {
                    "key": "policy_or_document_reference",
                    "value": "star_health:star_comprehensive",
                    "source_reference": "test",
                    "sequence": 1,
                },
                {
                    "key": "requested_fact",
                    "value": "room_rent_limit",
                    "source_reference": "test",
                    "sequence": 1,
                },
            ],
        )
    )
    return intent, context


def test_direct_fact_plan_uses_requested_fact_for_all_evidence_subjects():
    intent, context = _room_rent_context()
    plan = ReasoningPlanner().plan(
        build_plan_input(
            request_id="p2b-plan",
            intent_analysis=intent,
            context_assessment=context,
        )
    )

    assert plan.plan_type == "DIRECT_FACT_PLAN"
    assert tuple(req.evidence_category for req in plan.required_evidence) == (
        "POLICY_WORDING",
        "POLICY_SCHEDULE",
        "NORMALIZED_POLICY_FACT",
    )
    assert tuple(req.subject_reference for req in plan.required_evidence) == (
        "requested_fact",
        "requested_fact",
        "requested_fact",
    )


def test_active_context_values_are_projected_for_evidence_semantics():
    _, context = _room_rent_context()

    assert _resolved_context_values(context) == {
        "policy_or_document_reference": "star_health:star_comprehensive",
        "requested_fact": "room_rent_limit",
    }
