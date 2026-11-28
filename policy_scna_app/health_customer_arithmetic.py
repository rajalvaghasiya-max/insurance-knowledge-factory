from __future__ import annotations

from pathlib import Path

from policy_scna_app.health_customer_v0 import (
    HealthConversationContext,
    HealthCustomerAnswerResult,
    ask_health_question as _ask_health_question,
    ask_health_question_live as _ask_health_question_live,
)

def enrich_health_customer_result_with_arithmetic(
    *,
    question: str,
    result: HealthCustomerAnswerResult,
    conversation_context: HealthConversationContext | None = None,
) -> HealthCustomerAnswerResult:
    """Contain unbound numeric inputs until governed semantic binding is validated.

    The existing calculator remains available for explicitly typed callers.
    Customer text alone does not establish an operand's insurance role.
    Preserve the original governed answer and its release decision unchanged.
    See #466 and #468.
    """
    return result


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
