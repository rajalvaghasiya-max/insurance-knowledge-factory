from __future__ import annotations

import pytest

from insurance_intelligence.contracts.intent import build_input
from insurance_intelligence.intent.analyzer import IntentAnalyzer
from insurance_intelligence.intent.taxonomy import GOVERNED_INTENT_LABELS

analyzer = IntentAnalyzer()


def _analyze(text: str, **kwargs):
    return analyzer.analyze(build_input(request_id="test-request", text=text, **kwargs))


# --- Representative scenarios (MO-013 s10) ----------------------------------


def test_term_explanation():
    result = _analyze("What is a deductible?")
    assert result.primary_intent == "TERM_EXPLANATION"


def test_policy_fact_lookup():
    result = _analyze("What is the co-pay percentage in this policy?")
    assert result.primary_intent == "POLICY_FACT_LOOKUP"


def test_clause_implication():
    result = _analyze("How will room-rent capping affect my claim?")
    assert result.primary_intent == "CLAUSE_IMPLICATION"


def test_product_explanation():
    result = _analyze("Help me understand Aditya Birla Activ One Max.")
    assert result.primary_intent == "PRODUCT_EXPLANATION"


def test_advisor_explanation():
    result = _analyze("How do I explain this plan to my customer?")
    assert result.primary_intent == "ADVISOR_EXPLANATION"


def test_product_comparison():
    result = _analyze("Compare Activ One Max and Star Comprehensive.")
    assert result.primary_intent == "PRODUCT_COMPARISON"


def test_quote_comparison():
    result = _analyze("Compare these two insurance quotes.")
    assert result.primary_intent == "QUOTE_COMPARISON"


def test_coverage_check():
    result = _analyze("Does this policy cover cataract surgery?")
    assert result.primary_intent == "COVERAGE_CHECK"


def test_exclusion_check():
    result = _analyze("Is cosmetic surgery excluded?")
    assert result.primary_intent == "EXCLUSION_CHECK"


def test_claim_scenario():
    result = _analyze("My hospital bill is ₹5 lakh and my policy has a 20% co-pay. What happens?")
    assert result.primary_intent == "CLAIM_SCENARIO"


def test_calculation():
    result = _analyze("What is 20% of a ₹5 lakh admissible claim?")
    assert result.primary_intent == "CALCULATION"


def test_recommendation():
    result = _analyze("Should I increase my base policy or buy a super top-up?")
    assert result.primary_intent == "RECOMMENDATION"
    assert "SUITABILITY_ASSESSMENT" in result.secondary_intents or result.secondary_intents == ()


def test_document_interpretation():
    result = _analyze("Please explain this clause from my policy.")
    assert result.primary_intent == "DOCUMENT_INTERPRETATION"


def test_follow_up_with_prior_context():
    result = _analyze(
        "What is its biggest weakness?",
        conversation_context=[{"role": "user", "text": "Explain Activ One Max.", "sequence": 1}],
        known_entity_mentions=[
            {"entity_type": "PRODUCT", "surface_text": "Activ One Max", "normalized_text": "activ one max"}
        ],
    )
    assert result.follow_up.is_follow_up is True
    assert result.follow_up.reference_type == "prior_candidate_entity"
    # Governed choice for this v0.1 baseline; documented and tested per MO-013 s10.
    assert result.primary_intent == "PRODUCT_EXPLANATION"
    assert result.analysis_status == "CLASSIFIED"


def test_ambiguous_pronoun_without_context_requires_clarification():
    result = _analyze("Is it good?")
    assert result.analysis_status == "CLARIFICATION_REQUIRED"
    assert result.clarification_question


def test_missing_comparison_target_requires_clarification():
    result = _analyze("Compare this with the other one.")
    assert result.analysis_status == "CLARIFICATION_REQUIRED"
    assert result.clarification_question
    assert result.clarification_question.strip() != "Please provide more information."


def test_out_of_scope():
    result = _analyze("What is the weather today?")
    assert result.analysis_status == "OUT_OF_SCOPE"
    assert result.primary_intent == "OUT_OF_SCOPE"


def test_invalid_request_empty_input():
    result = _analyze("   ")
    assert result.analysis_status == "INVALID_REQUEST"


# --- Precedence rules (MO-013 s4) -------------------------------------------


def test_precedence_recommendation_over_suitability():
    result = _analyze("What should I buy?")
    assert result.primary_intent == "RECOMMENDATION"


def test_precedence_clause_implication_over_term_explanation():
    result = _analyze("What is room-rent capping and how will it affect my claim?")
    assert result.primary_intent == "CLAUSE_IMPLICATION"


def test_precedence_advisor_explanation_over_product_explanation():
    result = _analyze("How do I explain this plan to my customer?")
    assert result.primary_intent == "ADVISOR_EXPLANATION"


def test_precedence_product_comparison_not_recommendation_without_choice_language():
    result = _analyze("Compare Plan A and Plan B.")
    assert result.primary_intent == "PRODUCT_COMPARISON"
    assert result.primary_intent != "RECOMMENDATION"


def test_precedence_document_interpretation_with_clause_implication_secondary():
    result = _analyze("Please explain this clause from my policy.")
    assert result.primary_intent == "DOCUMENT_INTERPRETATION"


# --- Candidate entity boundary (MO-013 s5) ----------------------------------


def test_candidate_entities_are_mentions_not_governed_ids():
    result = _analyze("Explain Activ One Max to me.")
    product_mentions = [e for e in result.candidate_entities if e.entity_type == "PRODUCT"]
    assert product_mentions
    for entity in product_mentions:
        assert entity.normalized_text == "activ one max"
        # No governed-id-shaped value (e.g. "insurer:product") is ever produced.
        assert ":" not in entity.normalized_text


def test_candidate_entities_extract_financial_value_and_age():
    result = _analyze("Would this suit a 58-year-old with a ₹5 lakh claim?")
    types_found = {e.entity_type for e in result.candidate_entities}
    assert "AGE" in types_found
    assert "FINANCIAL_VALUE" in types_found


# --- Invariants (MO-013 s11) -------------------------------------------------


def test_output_contract_version_present():
    result = _analyze("What is a deductible?")
    assert result.contract_version == "1.0"


def test_request_id_preserved():
    result = analyzer.analyze(build_input(request_id="my-request-42", text="What is a deductible?"))
    assert result.request_id == "my-request-42"


def test_primary_intent_is_governed():
    result = _analyze("What is a deductible?")
    assert result.primary_intent in GOVERNED_INTENT_LABELS


def test_secondary_intents_are_governed_and_unique():
    result = _analyze("What is the co-pay percentage in this policy?")
    assert len(result.secondary_intents) == len(set(result.secondary_intents))
    for label in result.secondary_intents:
        assert label in GOVERNED_INTENT_LABELS


def test_primary_intent_not_duplicated_as_secondary():
    for text in (
        "What is a deductible?",
        "What is the co-pay percentage in this policy?",
        "How will room-rent capping affect my claim?",
        "Should I increase my base policy or buy a super top-up?",
    ):
        result = _analyze(text)
        assert result.primary_intent not in result.secondary_intents


def test_confidence_between_zero_and_one():
    for text in ("What is a deductible?", "Is it good?", "What is the weather today?", "   "):
        result = _analyze(text)
        assert 0.0 <= result.confidence <= 1.0


def test_candidate_entities_never_contain_governed_ids():
    result = _analyze("Explain Star Comprehensive and Activ One Max to me.")
    for entity in result.candidate_entities:
        assert ":" not in entity.normalized_text
        assert not entity.normalized_text.startswith("star_health")
        assert not entity.normalized_text.startswith("aditya_birla")


def test_clarification_required_includes_a_question():
    result = _analyze("Is it good?")
    assert result.analysis_status == "CLARIFICATION_REQUIRED"
    assert result.clarification_question is not None and result.clarification_question.strip()


def test_non_clarification_results_have_no_clarification_question():
    result = _analyze("What is a deductible?")
    assert result.analysis_status != "CLARIFICATION_REQUIRED"
    assert result.clarification_question is None


def test_empty_input_fails_safely():
    result = _analyze("")
    assert result.analysis_status == "INVALID_REQUEST"


def test_deterministic_repeated_runs_produce_identical_output():
    request = build_input(request_id="determinism-check", text="How will room-rent capping affect my claim?")
    first = analyzer.analyze(request)
    second = analyzer.analyze(request)
    assert first == second


def test_no_evidence_lookup_or_network_call():
    """Structural guarantee: the analyzer module imports no HTTP, file-IO,
    or Knowledge Factory retrieval dependency."""
    import insurance_intelligence.intent.analyzer as analyzer_module

    source = open(analyzer_module.__file__, encoding="utf-8").read()
    forbidden_imports = ("import requests", "import urllib", "factory_core.canonical", "knowledge_domains")
    for forbidden in forbidden_imports:
        assert forbidden not in source, f"analyzer.py must not import {forbidden!r}"


def test_no_llm_or_external_dependency_imported():
    import insurance_intelligence.intent.analyzer as analyzer_module
    import insurance_intelligence.contracts.intent as contracts_module

    for module in (analyzer_module, contracts_module):
        source = open(module.__file__, encoding="utf-8").read()
        for forbidden in ("openai", "anthropic", "langchain", "transformers"):
            assert forbidden not in source.lower()


# --- Unknown product name should not block classification (MO-013 s9) ------


def test_unknown_product_name_still_classifies():
    result = _analyze("Explain SuperMegaHealth Platinum Plus to me.")
    assert result.primary_intent == "PRODUCT_EXPLANATION"
    assert result.analysis_status in ("CLASSIFIED", "CLASSIFIED_WITH_AMBIGUITY")
