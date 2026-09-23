from __future__ import annotations

from insurance_intelligence.terminology.concept_resolver import CanonicalConceptResolver
from insurance_intelligence.terminology.health_seed import build_health_concept_registry_v1


def _resolver() -> CanonicalConceptResolver:
    return CanonicalConceptResolver(build_health_concept_registry_v1())


def test_case_a_resolves_ped_and_waiting_period_mentions_in_question_order() -> None:
    mentions = _resolver().resolve_mentions(
        "What is the PED waiting period in Star Comprehensive?",
        domain="health",
    )

    assert tuple(item.selected_concept.concept_id for item in mentions) == (
        "health:concept:pre_existing_disease",
        "health:concept:waiting_period",
    )


def test_multi_concept_resolution_rejects_near_but_not_governed_language() -> None:
    mentions = _resolver().resolve_mentions(
        "What is the waiting-ish period for an old illness?",
        domain="health",
    )

    assert mentions == ()


def test_multi_concept_resolution_does_not_choose_ambiguous_governed_phrase() -> None:
    mentions = _resolver().resolve_mentions(
        "How much is the amount I pay myself?",
        domain="health",
    )

    assert mentions == ()


def test_multi_concept_resolution_uses_word_boundaries_for_short_aliases() -> None:
    mentions = _resolver().resolve_mentions(
        "This question is about basic coverage, not an SI value.",
        domain="health",
    )

    assert tuple(item.selected_concept.concept_id for item in mentions) == (
        "health:concept:sum_insured",
    )
