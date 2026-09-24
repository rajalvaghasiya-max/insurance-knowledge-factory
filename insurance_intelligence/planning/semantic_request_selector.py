"""Deterministic question-relative selector for governed topic components."""
from __future__ import annotations

import re
from collections.abc import Sequence

from insurance_intelligence.contracts.topic_completeness import TopicDefinition


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", value.lower()))


def _match_score(question_tokens: set[str], request_term: str) -> tuple[int, int] | None:
    term_tokens = _tokens(request_term)
    if not term_tokens:
        return None
    if not set(term_tokens).issubset(question_tokens):
        return None
    return (len(set(term_tokens)), len(request_term.strip()))


def select_requested_semantic_component(
    *,
    question: str,
    definition: TopicDefinition | Sequence[TopicDefinition],
) -> str | None:
    """Return one uniquely best governed component match, otherwise None.

    Request terms are governed token bundles stored on TopicComponentDefinition.
    A bundle matches when all of its normalized tokens occur in the question.
    The most specific bundle wins by token count, then bundle length. Any tie
    across different topic/components fails closed.
    """
    if not isinstance(question, str) or not question.strip():
        return None

    definitions = (
        (definition,)
        if isinstance(definition, TopicDefinition)
        else tuple(definition)
    )
    if not definitions or any(not isinstance(item, TopicDefinition) for item in definitions):
        raise TypeError("definition must be TopicDefinition or a sequence of TopicDefinition values")

    question_tokens = set(_tokens(question))
    matches: list[tuple[tuple[int, int], str, str]] = []

    for topic in definitions:
        for component in topic.components:
            for request_term in component.request_terms:
                score = _match_score(question_tokens, request_term)
                if score is not None:
                    matches.append((score, topic.topic_id, component.component_id))

    if not matches:
        return None

    best_score = max(item[0] for item in matches)
    best = {
        (topic_id, component_id)
        for score, topic_id, component_id in matches
        if score == best_score
    }
    if len(best) != 1:
        return None
    return next(iter(best))[1]


__all__ = ["select_requested_semantic_component"]
