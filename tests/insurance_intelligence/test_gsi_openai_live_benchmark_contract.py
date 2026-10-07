from __future__ import annotations

import inspect
import json

import pytest

from insurance_intelligence.semantic_interpretation.provider_adapter import build_semantic_text_request
from scripts import run_gsi_openai_live_benchmark as live


def test_live_benchmark_requires_explicit_key_and_model() -> None:
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        live.live_config_from_env({})
    with pytest.raises(RuntimeError, match="POLICYSCNA_GSI_MODEL"):
        live.live_config_from_env({"OPENAI_API_KEY": "key"})
    config = live.live_config_from_env(
        {"OPENAI_API_KEY": "key", "POLICYSCNA_GSI_MODEL": "explicit-model"}
    )
    assert config.api_key == "key"
    assert config.model == "explicit-model"


def test_live_benchmark_contains_precommitted_held_back_restoration_cases() -> None:
    held_back = tuple(case for case in live.CASES if case.held_back)
    assert held_back
    assert all(case.expected_concept_id == live.HELD_BACK_CONCEPT_ID for case in held_back)
    assert live.HELD_BACK_CONCEPT_ID == "health:concept:restoration"


def test_runtime_provider_adapter_remains_free_of_restoration_specific_logic() -> None:
    from insurance_intelligence.semantic_interpretation import provider_adapter

    source = inspect.getsource(provider_adapter).lower()
    assert "restoration" not in source


def test_semantic_request_supplies_strict_schema_from_governed_domains() -> None:
    vocabulary = live.benchmark_vocabulary()
    request = build_semantic_text_request(
        request_id="schema-contract",
        user_text="What does this mean?",
        vocabulary=vocabulary,
        provider_name="openai_responses",
        model_name="explicit-model",
        timeout_seconds=10,
    )
    assert request.response_schema_name == "governed_semantic_interpretation"
    assert request.response_json_schema is not None
    schema = json.loads(request.response_json_schema)
    assert schema["additionalProperties"] is False
    properties = schema["properties"]
    assert "resolution_threshold" not in properties
    assert "provenance" not in properties
    assert "CLAIM_PAYMENT_OUTCOME" not in properties["requested_outcome"]["enum"]
    assert "CLAIM_ADMISSIBILITY" not in properties["requested_outcome"]["enum"]
    assert set(properties["selected_concept_id"]["enum"][:-1]) == set(vocabulary.concept_ids)
