from __future__ import annotations

from insurance_intelligence.terminology.concept_resolver import CanonicalConceptResolver
from insurance_intelligence.terminology.health_seed import build_health_concept_registry_v1


def test_case_a_resolves_both_governed_concept_mentions() -> None:
    resolver = CanonicalConceptResolver(build_health_concept_registry_v1())

    mentions = resolver.resolve_mentions(
        "What is the PED waiting period in Star Comprehensive?",
        domain="health",
    )

    assert tuple(item.selected_concept.concept_id for item in mentions) == (
        "health:concept:pre_existing_disease",
        "health:concept:waiting_period",
    )


def test_multi_concept_resolution_remains_exact_and_fail_closed() -> None:
    resolver = CanonicalConceptResolver(build_health_concept_registry_v1())

    mentions = resolver.resolve_mentions(
        "What is the waiting-ish period for an old illness?",
        domain="health",
    )

    assert mentions == ()
