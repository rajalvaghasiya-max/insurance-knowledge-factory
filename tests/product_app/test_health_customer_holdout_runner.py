from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from insurance_intelligence.llm.provider import TextProviderRequest, TextProviderResponse
from scripts.run_health_customer_v0_holdout import (
    BenchmarkExecutionIntegrityError,
    run_holdout,
)


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


class _FailedTextProvider:
    provider_name = "failed_text_fake"

    def __init__(self) -> None:
        self.call_count = 0

    def complete(self, request: TextProviderRequest) -> TextProviderResponse:
        self.call_count += 1
        return TextProviderResponse(
            provider_request_id=request.provider_request_id,
            status="FAILED",
            error_message="OpenAI Responses HTTP status 401",
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


def _holdout(cases: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "benchmark_id": "health-customer-v0-independent-holdout-v1",
        "benchmark_role": "HOLDOUT_UNSEEN",
        "author_declaration": {
            "independent": True,
            "author_or_model": "independent-author",
            "fresh_session_or_equivalent": True,
            "date_authored": "2026-11-14",
        },
        "conversations": [
            {
                "conversation_id": "holdout-conv-test",
                "cases": cases,
            }
        ],
    }


def test_holdout_runner_executes_frozen_shape_with_context(tmp_path: Path) -> None:
    holdout = _holdout(
        [
            {
                "case_id": "holdout-case-test-1",
                "turn_index": 1,
                "prior_context_required": False,
                "concept_area": "pre_existing_disease",
                "user_text": "What does pre-existing disease mean?",
                "reference": {
                    "must_include": ["Explain PED."],
                    "legitimate_dependency": ["Exact application depends on policy facts."],
                    "must_not_imply": ["Do not guarantee coverage."],
                    "acceptable_clarification": ["Ask for policy details only for exact application."],
                    "unnecessary_deferral": ["General explanation can be given now."],
                },
            },
            {
                "case_id": "holdout-case-test-2",
                "turn_index": 2,
                "prior_context_required": True,
                "concept_area": "pre_existing_disease",
                "user_text": "And what should I check in my policy?",
                "reference": {
                    "must_include": ["Use prior PED context."],
                    "legitimate_dependency": ["Exact terms depend on policy facts."],
                    "must_not_imply": ["Do not infer exact dates."],
                    "acceptable_clarification": ["Ask for wording if exact answer is wanted."],
                    "unnecessary_deferral": ["Give a useful checklist."],
                },
            },
        ]
    )
    holdout_path = tmp_path / "holdout.json"
    holdout_path.write_text(json.dumps(holdout, sort_keys=True), encoding="utf-8")
    expected_sha = hashlib.sha256(holdout_path.read_bytes()).hexdigest()

    provider = _QueuedTextProvider(
        [
            _resolved_output("health:concept:pre_existing_disease"),
            _resolved_output("health:concept:pre_existing_disease"),
        ]
    )

    report = run_holdout(
        provider=provider,
        model_name="test-model",
        holdout_path=holdout_path,
        repository_root=ROOT,
    )

    assert provider.call_count == 2
    assert report["source_holdout_sha256"] == expected_sha
    assert report["benchmark_role"] == "HOLDOUT_RUN"
    assert report["execution_integrity"] == "PASS"
    assert report["conversation_count"] == 1
    assert report["case_count"] == 2
    assert report["released_text_count"] == 2
    assert report["quality_scoring"] == "NOT_SCORED"
    assert [case["context_turn_count_before"] for case in report["cases"]] == [0, 1]
    assert [case["context_turn_count_after"] for case in report["cases"]] == [1, 2]
    assert all(case["interpretation_attempt_status"] == "RESOLVED" for case in report["cases"])
    assert all(case["interpretation_failure_attribution"]["origin"] == "NONE" for case in report["cases"])
    assert all(case["reference"] for case in report["cases"])
    assert all(case["released_text"] for case in report["cases"])


def test_holdout_runner_invalidates_provider_failure_instead_of_scoring_clarification(
    tmp_path: Path,
) -> None:
    holdout = _holdout(
        [
            {
                "case_id": "holdout-case-provider-failure",
                "turn_index": 1,
                "prior_context_required": False,
                "concept_area": "pre_existing_disease",
                "user_text": "What does pre-existing disease mean?",
                "reference": {
                    "must_include": ["Explain PED."],
                    "legitimate_dependency": ["Exact application depends on policy facts."],
                    "must_not_imply": ["Do not guarantee coverage."],
                    "acceptable_clarification": ["Ask only for exact application."],
                    "unnecessary_deferral": ["General explanation can be given now."],
                },
            }
        ]
    )
    holdout_path = tmp_path / "holdout.json"
    holdout_path.write_text(json.dumps(holdout), encoding="utf-8")
    provider = _FailedTextProvider()

    with pytest.raises(BenchmarkExecutionIntegrityError) as caught:
        run_holdout(
            provider=provider,
            model_name="test-model",
            holdout_path=holdout_path,
            repository_root=ROOT,
        )

    assert provider.call_count == 1
    assert caught.value.case_id == "holdout-case-provider-failure"
    assert caught.value.completed_case_count == 0
    assert caught.value.failure_attribution["origin"] == "INTERPRETATION"
    assert caught.value.failure_attribution["detail"] == "OpenAI Responses HTTP status 401"
