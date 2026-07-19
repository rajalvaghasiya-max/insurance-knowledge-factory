from __future__ import annotations

import pytest

from insurance_intelligence.intent.taxonomy import (
    GOVERNED_INTENT_LABELS,
    GovernedIntentError,
    INTENT_DEFINITIONS,
    is_governed_intent,
    validate_intent_label,
)

EXPECTED_LABELS = {
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


def test_taxonomy_matches_approved_mo012_list_exactly():
    assert GOVERNED_INTENT_LABELS == EXPECTED_LABELS


def test_every_label_has_a_definition():
    assert set(INTENT_DEFINITIONS.keys()) == GOVERNED_INTENT_LABELS
    for label, definition in INTENT_DEFINITIONS.items():
        assert isinstance(definition, str) and definition.strip()


def test_is_governed_intent_true_for_valid_label():
    assert is_governed_intent("TERM_EXPLANATION") is True


def test_is_governed_intent_false_for_invalid_label():
    assert is_governed_intent("NOT_A_REAL_INTENT") is False
    assert is_governed_intent(None) is False
    assert is_governed_intent(123) is False


def test_validate_intent_label_returns_value_when_valid():
    assert validate_intent_label("CALCULATION") == "CALCULATION"


def test_validate_intent_label_raises_when_invalid():
    with pytest.raises(GovernedIntentError):
        validate_intent_label("MADE_UP_LABEL")


def test_taxonomy_is_immutable_collection_type():
    # frozenset and MappingProxyType are the deliberate immutability guards.
    assert isinstance(GOVERNED_INTENT_LABELS, frozenset)
    with pytest.raises(TypeError):
        INTENT_DEFINITIONS["NEW_LABEL"] = "should not be settable"  # type: ignore[index]
