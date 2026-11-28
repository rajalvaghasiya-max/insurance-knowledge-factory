from __future__ import annotations

import json

from insurance_intelligence.llm.provider import DeterministicFakeTextProvider
from policy_scna_app.health_customer_arithmetic import ask_health_question_with_arithmetic
from policy_scna_app.health_customer_v0 import HealthConversationContext, HealthConversationTurn


def _resolved_output(
    concept_id: str,
    *,
    semantic_fact: str,
    requested_outcome: str = "INSURANCE_MECHANICS_EXPLANATION",
) -> str:
    return json.dumps(
        {
            "interpretation_status": "RESOLVED",
            "confidence": 0.99,
            "primary_intent": "understand_policy_effect",
            "requested_outcome": requested_outcome,
            "governed_concept_candidates": [
                {"concept_id": concept_id, "confidence": 0.99}
            ],
            "selected_concept_id": concept_id,
            "requested_semantic_fact": semantic_fact,
            "scenario_facts": [],
            "request_authority_class": "ASSERTIVE",
            "ambiguity_reasons": [],
            "competing_interpretations": [],
        },
        sort_keys=True,
    )


def test_copay_single_amount_is_not_bound_automatically() -> None:
    provider = DeterministicFakeTextProvider(
        output_text=_resolved_output(
            "health:concept:copayment",
            semantic_fact="copay.percentage_and_basis",
        )
    )

    result = ask_health_question_with_arithmetic(
        question=(
            "For illustration, if the co-pay is 17.5% and the applicable calculation base "
            "is ₹80,000, what is the arithmetic?"
        ),
        provider=provider,
        model_name="test-model",
        request_id="health-v0-copay-arithmetic",
        execution_id="health-v0-copay-arithmetic-execution",
        created_at="2026-10-18T18:00:00Z",
    )

    assert result.status == "ANSWER"
    assert result.selected_topic == "conditional_copayment"
    assert result.render_outcome == "PASS"
    assert all(section.section_type != "CUSTOMER_EXPLANATION" for section in result.response.sections)
    assert "Using only the numbers you gave" not in result.released_text


def test_copay_multiple_amounts_are_not_bound_automatically() -> None:
    provider = DeterministicFakeTextProvider(
        output_text=_resolved_output(
            "health:concept:copayment",
            semantic_fact="copay.gross_bill_vs_admissible_amount",
        )
    )
    context = HealthConversationContext(
        turns=(
            HealthConversationTurn(
                customer_text="For this illustration use an 18% co-pay.",
                selected_concept_id="health:concept:copayment",
                selected_topic="conditional_copayment",
            ),
        )
    )

    result = ask_health_question_with_arithmetic(
        question="The gross bill is ₹90,000 but another relevant amount is ₹75,000. What then?",
        provider=provider,
        model_name="test-model",
        request_id="health-v0-copay-conditional-bases",
        execution_id="health-v0-copay-conditional-bases-execution",
        created_at="2026-10-18T18:00:30Z",
        conversation_context=context,
    )

    assert result.status == "ANSWER"
    assert result.render_outcome == "PASS"
    assert all(section.section_type != "CUSTOMER_EXPLANATION" for section in result.response.sections)
    assert "Using only the numbers you gave" not in result.released_text


def test_copay_labeled_amount_is_not_bound_by_proximity() -> None:
    provider = DeterministicFakeTextProvider(
        output_text=_resolved_output(
            "health:concept:copayment",
            semantic_fact="copay.gross_bill_vs_admissible_amount",
        )
    )
    context = HealthConversationContext(
        turns=(
            HealthConversationTurn(
                customer_text="My policy has a 20% co-pay.",
                selected_concept_id="health:concept:copayment",
                selected_topic="conditional_copayment",
            ),
        )
    )

    result = ask_health_question_with_arithmetic(
        question=(
            "The hospital bill is ₹1,00,000 but only ₹80,000 is admissible. "
            "How is the 20% co-pay calculated?"
        ),
        provider=provider,
        model_name="test-model",
        request_id="health-v0-copay-labeled-admissible",
        execution_id="health-v0-copay-labeled-admissible-execution",
        created_at="2026-11-22T16:00:00Z",
        conversation_context=context,
    )

    assert result.status == "ANSWER"
    assert result.render_outcome == "PASS"
    assert all(section.section_type != "CUSTOMER_EXPLANATION" for section in result.response.sections)
    assert "Using only the numbers you gave" not in result.released_text


def test_room_rent_prior_amount_is_not_bound_automatically() -> None:
    provider = DeterministicFakeTextProvider(
        output_text=_resolved_output(
            "health:concept:room_rent_limit",
            semantic_fact="room.excess_consequence_boundary",
        )
    )
    context = HealthConversationContext(
        turns=(
            HealthConversationTurn(
                customer_text="For illustration, use a room limit of 2% of ₹3 lakh per day.",
                selected_concept_id="health:concept:room_rent_limit",
                selected_topic="room_rent_limit",
            ),
        )
    )

    result = ask_health_question_with_arithmetic(
        question="If the room costs ₹8,500 per day, what is the price difference?",
        provider=provider,
        model_name="test-model",
        request_id="health-v0-room-difference",
        execution_id="health-v0-room-difference-execution",
        created_at="2026-10-18T18:01:00Z",
        conversation_context=context,
    )

    assert result.status == "ANSWER"
    assert result.selected_topic == "room_rent_limit"
    assert result.render_outcome == "PASS"
    assert all(section.section_type != "CUSTOMER_EXPLANATION" for section in result.response.sections)
    assert "Using only the numbers you gave" not in result.released_text


def test_room_rent_proposed_difference_is_not_bound_automatically() -> None:
    provider = DeterministicFakeTextProvider(
        output_text=_resolved_output(
            "health:concept:room_rent_limit",
            semantic_fact="room.excess_consequence_boundary",
        )
    )
    context = HealthConversationContext(
        turns=(
            HealthConversationTurn(
                customer_text="For illustration, use a room limit of 2% of ₹3 lakh per day.",
                selected_concept_id="health:concept:room_rent_limit",
                selected_topic="room_rent_limit",
            ),
        )
    )

    result = ask_health_question_with_arithmetic(
        question="If the room is ₹8,500, am I definitely paying only the extra ₹2,500?",
        provider=provider,
        model_name="test-model",
        request_id="health-v0-room-proposed-difference",
        execution_id="health-v0-room-proposed-difference-execution",
        created_at="2026-10-18T18:01:30Z",
        conversation_context=context,
    )

    assert result.status == "ANSWER"
    assert result.render_outcome == "PASS"
    assert all(section.section_type != "CUSTOMER_EXPLANATION" for section in result.response.sections)
    assert "Using only the numbers you gave" not in result.released_text


def test_non_arithmetic_health_topic_is_not_enriched() -> None:
    provider = DeterministicFakeTextProvider(
        output_text=_resolved_output(
            "health:concept:pre_existing_disease",
            semantic_fact="ped.definition",
            requested_outcome="POLICY_FACT_EXPLANATION",
        )
    )

    result = ask_health_question_with_arithmetic(
        question="What does pre-existing disease mean?",
        provider=provider,
        model_name="test-model",
        request_id="health-v0-ped-no-arithmetic",
        execution_id="health-v0-ped-no-arithmetic-execution",
        created_at="2026-10-18T18:02:00Z",
    )

    assert result.status == "ANSWER"
    assert all(section.section_type != "CUSTOMER_EXPLANATION" for section in result.response.sections)


def test_non_admissible_followup_is_not_treated_as_calculation_base() -> None:
    provider = DeterministicFakeTextProvider(
        output_text=_resolved_output(
            "health:concept:copayment",
            semantic_fact="copay.gross_bill_vs_admissible_amount",
        )
    )
    context = HealthConversationContext(
        turns=(
            HealthConversationTurn(
                customer_text="My policy has a 15% co-pay. The hospital bill is ₹1,50,000 and the admissible claim amount is ₹1,20,000.",
                selected_concept_id="health:concept:copayment",
                selected_topic="conditional_copayment",
            ),
        )
    )
    result = ask_health_question_with_arithmetic(
        question="What if ₹30,000 of the hospital bill is not admissible?",
        provider=provider,
        model_name="test-model",
        request_id="health-v0-contain-non-admissible",
        execution_id="health-v0-contain-non-admissible-execution",
        created_at="2026-11-28T10:00:00Z",
        conversation_context=context,
    )
    assert result.status == "ANSWER"
    assert result.render_outcome == "PASS"
    assert "₹4,500" not in result.released_text
    assert "Using only the numbers you gave" not in result.released_text
    assert all(section.section_type != "CUSTOMER_EXPLANATION" for section in result.response.sections)
