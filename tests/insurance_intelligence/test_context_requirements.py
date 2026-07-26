from __future__ import annotations

from insurance_intelligence.context.requirements import REQUIREMENT_REGISTRY, requirements_for_intent
from insurance_intelligence.intent.taxonomy import GOVERNED_INTENT_LABELS


def test_all_registry_intents_are_governed():
    for requirement in REQUIREMENT_REGISTRY:
        assert requirement.intent in GOVERNED_INTENT_LABELS


def test_all_requirement_ids_are_unique():
    ids = [r.requirement_id for r in REQUIREMENT_REGISTRY]
    assert len(ids) == len(set(ids))


def test_term_explanation_baseline():
    reqs = requirements_for_intent("TERM_EXPLANATION")
    keys = {r.context_key: r.required for r in reqs}
    assert keys["term_or_concept"] is True
    assert keys["policy_reference"] is False
    assert keys["product_reference"] is False


def test_product_comparison_requires_two_subjects():
    reqs = requirements_for_intent("PRODUCT_COMPARISON")
    required_keys = {r.context_key for r in reqs if r.required}
    assert required_keys == {"comparison_subject_1", "comparison_subject_2"}


def test_recommendation_has_high_context_burden():
    reqs = requirements_for_intent("RECOMMENDATION")
    required_keys = {r.context_key for r in reqs if r.required}
    assert {"decision_options", "user_objective", "existing_coverage", "age", "family_composition", "budget"} <= required_keys
    assert sum(1 for r in reqs if r.required) >= 6


def test_out_of_scope_has_no_requirements():
    assert requirements_for_intent("OUT_OF_SCOPE") == ()


def test_clause_implication_clause_required_reference_optional():
    reqs = requirements_for_intent("CLAUSE_IMPLICATION")
    by_key = {r.context_key: r for r in reqs}
    assert by_key["clause_or_feature"].required is True
    assert by_key["policy_or_product_reference"].required is False


def test_every_requirement_has_specific_clarification_question():
    for requirement in REQUIREMENT_REGISTRY:
        assert requirement.clarification_question.strip()
        assert requirement.clarification_question.strip().lower() != "please provide more information."
