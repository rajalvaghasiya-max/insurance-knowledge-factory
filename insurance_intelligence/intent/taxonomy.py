"""Governed intent taxonomy for the PolicyScna Insurance Intelligence
Layer (MO-012 / MO-013).

This taxonomy is centrally defined, immutable at runtime, and
extensible only through code change and review. Runtime components
must select intent labels only from GOVERNED_INTENT_LABELS -- no
component may introduce a new label dynamically.
"""
from __future__ import annotations

from types import MappingProxyType

# Ordered for readability; order carries no runtime meaning.
GOVERNED_INTENT_LABELS: frozenset[str] = frozenset(
    {
        "TERM_EXPLANATION",
        "POLICY_FACT_LOOKUP",
        "POLICY_SUMMARY",
        "COVERAGE_CHECK",
        "EXCLUSION_CHECK",
        "CLAIM_SCENARIO",
        "CLAUSE_IMPLICATION",
        "PRODUCT_EXPLANATION",
        "PRODUCT_COMPARISON",
        "POLICY_COMPARISON",
        "QUOTE_COMPARISON",
        "SUITABILITY_ASSESSMENT",
        "RECOMMENDATION",
        "CALCULATION",
        "DOCUMENT_INTERPRETATION",
        "ADVISOR_EXPLANATION",
        "CLARIFICATION_RESPONSE",
        "FOLLOW_UP",
        "OUT_OF_SCOPE",
    }
)

# Concise, human-readable definitions -- documentation, not behaviour.
INTENT_DEFINITIONS: MappingProxyType[str, str] = MappingProxyType(
    {
        "TERM_EXPLANATION": "The user wants a general definition of an insurance term, not tied to their specific policy.",
        "POLICY_FACT_LOOKUP": "The user wants a specific fact stated in their own policy or product.",
        "POLICY_SUMMARY": "The user wants an overview summary of their policy.",
        "COVERAGE_CHECK": "The user wants to know whether something is covered.",
        "EXCLUSION_CHECK": "The user wants to know whether something is excluded.",
        "CLAIM_SCENARIO": "The user describes a hypothetical or real claim situation and wants to understand the outcome.",
        "CLAUSE_IMPLICATION": "The user wants to know what a specific clause or term means in practice for their situation.",
        "PRODUCT_EXPLANATION": "The user wants an explanation of a specific insurance product.",
        "PRODUCT_COMPARISON": "The user wants two or more products compared.",
        "POLICY_COMPARISON": "The user wants two or more of their own policies compared.",
        "QUOTE_COMPARISON": "The user wants two or more quotes compared.",
        "SUITABILITY_ASSESSMENT": "The user wants an assessment of whether a product or option suits their situation.",
        "RECOMMENDATION": "The user wants a directive suggestion about what to choose or do.",
        "CALCULATION": "The user wants a numeric computation performed.",
        "DOCUMENT_INTERPRETATION": "The user wants a specific passage from a document explained.",
        "ADVISOR_EXPLANATION": "The user (an advisor) wants an explanation framed for communicating to their own client.",
        "CLARIFICATION_RESPONSE": "The user's message is a direct response to a clarification question the system asked.",
        "FOLLOW_UP": "The user's message continues a prior conversational thread and depends on it for interpretation.",
        "OUT_OF_SCOPE": "The request is not an insurance-intelligence request.",
    }
)


class GovernedIntentError(ValueError):
    """Raised when a value outside the governed taxonomy is used."""


def is_governed_intent(label: object) -> bool:
    return isinstance(label, str) and label in GOVERNED_INTENT_LABELS


def validate_intent_label(label: object, *, field_label: str = "intent") -> str:
    if not is_governed_intent(label):
        raise GovernedIntentError(
            f"{field_label} must be one of the governed intent labels; got {label!r}"
        )
    return label  # type: ignore[return-value]
