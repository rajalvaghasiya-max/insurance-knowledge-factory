from __future__ import annotations

import json
from pathlib import Path

from insurance_intelligence.llm.provider import TextProviderRequest, TextProviderResponse
from scripts.run_health_customer_v0_dev36 import DEFAULT_MANIFEST, _load_conversations, run_benchmark

ROOT = Path(__file__).resolve().parents[2]


class _QueuedTextProvider:
    provider_name = "queued_text_fake"

    def __init__(self, outputs: list[str]) -> None:
        self._outputs = list(outputs)
        self.call_count = 0

    def complete(self, request: TextProviderRequest) -> TextProviderResponse:
        output = self._outputs[self.call_count]
        self.call_count += 1
        return TextProviderResponse(
            provider_request_id=request.provider_request_id,
            status="SUCCEEDED",
            output_text=output,
        )


def _resolved_output(concept_id: str) -> str:
    return json.dumps(
        {
            "interpretation_status": "RESOLVED",
            "confidence": 0.99,
            "primary_intent": "understand_policy_term",
            "requested_outcome": "POLICY_FACT_EXPLANATION",
            "governed_concept_candidates": [
                {"concept_id": concept_id, "confidence": 0.99}
            ],
            "selected_concept_id": concept_id,
            "requested_semantic_fact": "definition",
            "scenario_facts": [],
            "request_authority_class": "ASSERTIVE",
            "ambiguity_reasons": [],
            "competing_interpretations": [],
        },
        sort_keys=True,
    )


def test_dev36_runner_executes_all_conversations_with_context_handoff() -> None:
    manifest = ROOT / DEFAULT_MANIFEST
    conversations = _load_conversations(manifest)
    expected_concepts = [
        str(case["expected_concept_id"])
        for conversation in conversations
        for case in conversation["cases"]
    ]
    provider = _QueuedTextProvider([_resolved_output(value) for value in expected_concepts])

    report = run_benchmark(
        provider=provider,
        model_name="test-model",
        manifest_path=manifest,
        repository_root=ROOT,
    )

    assert provider.call_count == 36
    assert report["conversation_count"] == 12
    assert report["case_count"] == 36
    assert report["released_text_count"] == 36
    assert report["wrong_concept_count"] == 0
    assert report["product_path_readiness"] == "PASS"
    assert report["quality_scoring"] == "NOT_SCORED"

    cases = report["cases"]
    assert [case["context_turn_count_before"] for case in cases[:3]] == [0, 1, 2]
    assert [case["context_turn_count_after"] for case in cases[:3]] == [1, 2, 3]
    assert all(case["render_outcome"] == "PASS" for case in cases)
    assert all(case["route_match"] is True for case in cases)
