"""Deterministic question-relative semantic component selection.

Selection is driven only by versioned TopicDefinition metadata.  The selector has no
insurer, product, or topic branches and does not inspect publication claim text.
"""
from __future__ import annotations

import re

from insurance_intelligence.contracts.topic_completeness import TopicDefinition


class TopicComponentSelectionError(ValueError):
    """Raised when component selection input is structurally invalid."""


def _normalize(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.casefold()).split())


def select_direct_component(
    definition: TopicDefinition,
    requested_outcome: str,
) -> str | None:
    """Select one direct-answer component from governed topic metadata.

    Explicit governed aliases take precedence over the topic default.  If aliases from
    more than one component are present, selection is ambiguous and returns None.
    """
    if not isinstance(definition, TopicDefinition):
        raise TopicComponentSelectionError(
            "definition must be a TopicDefinition"
        )
    if not isinstance(requested_outcome, str):
        raise TopicComponentSelectionError(
            "requested_outcome must be text"
        )

    query = _normalize(requested_outcome)
    if not query:
        return None

    matched_components: set[str] = set()
    padded_query = f" {query} "
    for component in definition.components:
        for alias in component.query_aliases:
            normalized_alias = _normalize(alias)
            if normalized_alias and f" {normalized_alias} " in padded_query:
                matched_components.add(component.component_id)

    if len(matched_components) == 1:
        return next(iter(matched_components))
    if len(matched_components) > 1:
        return None
    return definition.default_direct_component_id


__all__ = [
    "TopicComponentSelectionError",
    "select_direct_component",
]
