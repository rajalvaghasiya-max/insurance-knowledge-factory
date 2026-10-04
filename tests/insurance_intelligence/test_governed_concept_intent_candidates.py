from __future__ import annotations

from insurance_intelligence.contracts.intent import build_input as build_intent_input
from insurance_intelligence.intent.analyzer import IntentAnalyzer
from insurance_intelligence.terminology.concept_resolver import CanonicalConceptResolver
from insurance_intelligence.terminology.health_seed import build_health_concept_registry_v1


def _analyzer() -> IntentAnalyzer:
    return IntentAnalyzer(
        concept_resolver=CanonicalConceptResolver(build_health_concept_registry_v1())
    )


def test_governed_benefit_mention_becomes_non_authoritative_claim_concept_candidate():
    output = _analyzer().analyze(
        build_intent_input(
            request_id="governed-benefit-mention",
            text="Does Star Comprehensive cover bariatric surgery?",
            domain_hint="health",
        )
    )

    assert output.primary_intent == "COVERAGE_CHECK"
    candidates = tuple(
        item for item in output.candidate_entities
        if item.entity_type == "CLAIM_CONCEPT"
    )
    assert tuple(
        (item.normalized_text, item.source)
        for item in candidates
    ) == (("bariatric_surgery", "governed_concept_registry"),)


def test_analyzer_without_injected_registry_preserves_legacy_behavior():
    output = IntentAnalyzer().analyze(
        build_intent_input(
            request_id="no-registry",
            text="Does Star Comprehensive cover bariatric surgery?",
            domain_hint="health",
        )
    )

    assert output.primary_intent == "COVERAGE_CHECK"
    assert not any(
        item.normalized_text == "bariatric_surgery"
        for item in output.candidate_entities
    )
