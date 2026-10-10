from __future__ import annotations

import inspect

from insurance_intelligence.semantic_interpretation import provider_adapter
from insurance_intelligence.semantic_interpretation.provider_adapter import (
    ADAPTER_VERSION,
    GovernedInterpretationVocabulary,
    build_semantic_text_request,
)


def _request():
    vocabulary = GovernedInterpretationVocabulary(
        concept_ids=("concept_alpha", "concept_beta"),
        intent_ids=("understand_policy_term", "understand_policy_effect"),
        semantic_fact_ids=("definition", "mechanics"),
        scenario_fact_names=("context_detail", "customer_age"),
    )
    return build_semantic_text_request(
        request_id="contract-guidance",
        user_text="Explain what this means for my situation.",
        vocabulary=vocabulary,
        provider_name="deterministic_text_fake",
        model_name="test-model",
        timeout_seconds=5.0,
    )


def test_provider_guidance_distinguishes_language_ambiguity_from_unknown_policy_truth() -> None:
    prompt = _request().system_prompt
    assert "uncertainty about what the user means" in prompt
    assert "unknown downstream insurance truth do not by themselves" in prompt


def test_provider_guidance_encodes_resolved_and_nonresolved_contract_invariants() -> None:
    prompt = _request().system_prompt
    assert "If interpretation_status is RESOLVED" in prompt
    assert "ambiguity_reasons and competing_interpretations must both be empty" in prompt
    assert "use AMBIGUOUS or UNRESOLVED instead of RESOLVED" in prompt
    assert "selected_concept_id and requested_semantic_fact to null" in prompt


def test_provider_guidance_requires_unique_scenario_fact_names_and_merge() -> None:
    prompt = _request().system_prompt
    assert "Each scenario fact name may appear at most once" in prompt
    assert "merge those details into one value" in prompt


def test_provider_contract_repair_is_versioned_and_concept_neutral() -> None:
    assert ADAPTER_VERSION == "gsi-provider-adapter-v2"
    source = inspect.getsource(provider_adapter).lower()
    assert "restoration" not in source
