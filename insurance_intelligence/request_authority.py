"""Deterministic v1 classifier for the Assertion / Advisory request boundary."""
from __future__ import annotations

import re

from insurance_intelligence.contracts.request_authority import (
    RequestAuthorityInput,
    RequestAuthorityOutput,
    build_output,
)

ASSERTIVE_CUES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("what_is", re.compile(r"\bwhat\s+(?:is|are)\b", re.I)),
    ("what_does", re.compile(r"\bwhat\s+does\b", re.I)),
    ("how_much", re.compile(r"\bhow\s+much\b", re.I)),
    ("when", re.compile(r"\bwhen\b", re.I)),
    ("explain", re.compile(r"\b(?:explain|help\s+me\s+understand)\b", re.I)),
    ("covered", re.compile(r"\b(?:is|are|does)\b.{0,60}\bcover(?:ed|age)?\b", re.I)),
    ("compare", re.compile(r"\bcompare\b", re.I)),
    ("difference", re.compile(r"\b(?:difference|different)\b", re.I)),
    ("why", re.compile(r"\bwhy\b", re.I)),
)

ADVISORY_CUES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("should_i", re.compile(r"\bshould\s+(?:i|we)\b", re.I)),
    ("what_should", re.compile(r"\bwhat\s+should\s+(?:i|we|the\s+customer)\b", re.I)),
    ("recommend", re.compile(r"\b(?:recommend|recommendation|suggest)\b", re.I)),
    ("help_choose", re.compile(r"\bhelp\s+me\s+(?:choose|decide|pick)\b", re.I)),
    ("better_for_me", re.compile(r"\b(?:better|best|suitable)\s+(?:for\s+me|for\s+us|for\s+the\s+customer)\b", re.I)),
    ("which_better", re.compile(r"\bwhich\b.{0,50}\b(?:better|best|suitable)\b", re.I)),
    ("is_good", re.compile(r"\bis\b.{0,50}\b(?:good|right|suitable)\s+(?:for\s+me|for\s+us)?\b", re.I)),
    ("worth_it", re.compile(r"\bworth\s+(?:it|buying|keeping|taking)\b", re.I)),
    ("do_i_need", re.compile(r"\bdo\s+(?:i|we)\s+need\b", re.I)),
    ("what_can_i_do", re.compile(r"\bwhat\s+can\s+(?:i|we)\s+do\b", re.I)),
    ("what_would_you", re.compile(r"\bwhat\s+would\s+you\s+(?:do|choose|pick|recommend)\b", re.I)),
)


def _matches(text: str, registry: tuple[tuple[str, re.Pattern[str]], ...]) -> tuple[str, ...]:
    return tuple(name for name, pattern in registry if pattern.search(text))


def classify_request_authority(request: RequestAuthorityInput) -> RequestAuthorityOutput:
    """Classify requested authority without evidence access or insurance reasoning."""
    text = " ".join(request.text.split())
    assertive = _matches(text, ASSERTIVE_CUES)
    advisory = _matches(text, ADVISORY_CUES)

    if assertive and advisory:
        authority_class = "MIXED"
        guard = "SPLIT_ASSERTIVE_AND_ADVISORY_WITH_ADVISORY_SAFETY_REQUIRED"
        basis = "matched_assertive_and_advisory_cues"
        intent_allowed = True
    elif advisory:
        authority_class = "ADVISORY"
        guard = "ADVISORY_CONTEXT_AND_SAFETY_REQUIRED"
        basis = "matched_advisory_cues"
        intent_allowed = True
    elif assertive:
        authority_class = "ASSERTIVE"
        guard = "STANDARD_ASSERTION_GROUNDING"
        basis = "matched_assertive_cues"
        intent_allowed = True
    else:
        authority_class = "UNRESOLVED"
        guard = "CLARIFY_REQUESTED_AUTHORITY"
        basis = "no_governed_authority_cue_matched"
        intent_allowed = False

    return build_output(
        request_id=request.request_id,
        authority_class=authority_class,
        matched_assertive_cues=assertive,
        matched_advisory_cues=advisory,
        classification_basis=basis,
        downstream_guard=guard,
        intent_analysis_authorized=intent_allowed,
        recommendation_authorized=False,
        contract_version=request.contract_version,
    )
