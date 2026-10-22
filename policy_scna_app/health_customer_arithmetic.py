from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from insurance_intelligence.contracts.response import (
    ResponseAssemblerOutput,
    build_output as build_response_output,
    build_section as build_response_section,
)
from policy_scna_app.customer_arithmetic import (
    ArithmeticIllustration,
    build_conditional_percentage_illustration,
    build_difference_illustration,
    build_percentage_illustration,
    parse_percentages,
)
from policy_scna_app.health_customer_v0 import (
    HealthConversationContext,
    HealthCustomerAnswerResult,
    _release,
    ask_health_question as _ask_health_question,
    ask_health_question_live as _ask_health_question_live,
)

_COPAY_TOPIC = "conditional_copayment"
_ROOM_RENT_TOPIC = "room_rent_limit"


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _prior_customer_texts(context: HealthConversationContext | None) -> tuple[str, ...]:
    if context is None:
        return ()
    return tuple(turn.customer_text for turn in context.turns)


def _mentions_daily_basis(texts: tuple[str, ...]) -> bool:
    combined = " ".join(texts).casefold()
    return any(marker in combined for marker in ("per day", "per-day", "daily", "a day"))


def _illustration_for_resolved_topic(
    *,
    topic: str | None,
    question: str,
    context: HealthConversationContext | None,
) -> ArithmeticIllustration | None:
    prior = _prior_customer_texts(context)

    if topic == _COPAY_TOPIC:
        boundary = (
            "This arithmetic does not establish which amount the policy or claim assessment "
            "actually uses, or the final amount you would pay."
        )
        direct = build_percentage_illustration(
            current_text=question,
            prior_customer_texts=prior,
            basis_label="the amount you supplied as the co-pay calculation base",
            consequence_boundary=boundary,
        )
        if direct is not None:
            return direct
        return build_conditional_percentage_illustration(
            current_text=question,
            prior_customer_texts=prior,
            consequence_boundary=boundary,
        )

    if topic == _ROOM_RENT_TOPIC:
        if parse_percentages(question):
            return build_percentage_illustration(
                current_text=question,
                prior_customer_texts=prior,
                basis_label="the amount you supplied for this room-rent illustration",
                consequence_boundary=(
                    "This arithmetic does not establish the policy's applicable room entitlement, "
                    "any linked deduction, or your final out-of-pocket amount."
                ),
                per_day=_mentions_daily_basis((*prior, question)),
            )
        return build_difference_illustration(
            current_text=question,
            prior_customer_texts=prior,
            prior_percentage_basis_label="the earlier customer-supplied percentage and amount",
            consequence_boundary=(
                "This is only the room-price difference. It does not establish an insurer deduction "
                "or your final out-of-pocket amount."
            ),
        )

    return None


def _append_arithmetic_section(
    response: ResponseAssemblerOutput,
    illustration: ArithmeticIllustration,
) -> ResponseAssemblerOutput:
    section = build_response_section(
        section_id=_stable_id(
            "section",
            response.request_id,
            "customer-arithmetic",
            illustration.operation,
            illustration.result_amount,
        ),
        section_type="CUSTOMER_EXPLANATION",
        status="INCLUDED",
        text=illustration.text,
    )
    return build_response_output(
        request_id=response.request_id,
        response_id=_stable_id(
            "response",
            response.response_id,
            "customer-arithmetic",
            illustration.operation,
            illustration.result_amount,
        ),
        response_status=response.response_status,
        audience=response.audience,
        response_format=response.response_format,
        direct_answer=response.direct_answer,
        sections=(*response.sections, section),
        evidence_references=response.evidence_references,
        limitations=response.limitations,
        assumptions=response.assumptions,
        clarification_questions=response.clarification_questions,
        confidence=response.confidence,
        response_trace=response.response_trace,
        customer_reason=response.customer_reason,
    )


def enrich_health_customer_result_with_arithmetic(
    *,
    question: str,
    result: HealthCustomerAnswerResult,
    conversation_context: HealthConversationContext | None = None,
) -> HealthCustomerAnswerResult:
    """Add bounded arithmetic only after the governed Health answer has resolved safely."""
    if result.status != "ANSWER":
        return result

    illustration = _illustration_for_resolved_topic(
        topic=result.selected_topic,
        question=question,
        context=conversation_context,
    )
    if illustration is None:
        return result

    response = _append_arithmetic_section(result.response, illustration)
    released_text, render_outcome = _release(response)
    return HealthCustomerAnswerResult(
        request_id=result.request_id,
        status=result.status,
        selected_concept_id=result.selected_concept_id,
        selected_topic=result.selected_topic,
        response=response,
        interpretation=result.interpretation,
        released_text=released_text,
        render_outcome=render_outcome,
        next_context=result.next_context,
    )


def ask_health_question_with_arithmetic(
    *,
    question: str,
    conversation_context: HealthConversationContext | None = None,
    **kwargs,
) -> HealthCustomerAnswerResult:
    result = _ask_health_question(
        question=question,
        conversation_context=conversation_context,
        **kwargs,
    )
    return enrich_health_customer_result_with_arithmetic(
        question=question,
        result=result,
        conversation_context=conversation_context,
    )


def ask_health_question_live_with_arithmetic(
    question: str,
    *,
    repository_root: str | Path | None = None,
    conversation_context: HealthConversationContext | None = None,
) -> HealthCustomerAnswerResult:
    result = _ask_health_question_live(
        question,
        repository_root=repository_root,
        conversation_context=conversation_context,
    )
    return enrich_health_customer_result_with_arithmetic(
        question=question,
        result=result,
        conversation_context=conversation_context,
    )


__all__ = [
    "ask_health_question_live_with_arithmetic",
    "ask_health_question_with_arithmetic",
    "enrich_health_customer_result_with_arithmetic",
]
