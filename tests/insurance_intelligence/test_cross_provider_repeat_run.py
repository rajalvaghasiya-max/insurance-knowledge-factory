from __future__ import annotations

from copy import deepcopy

import pytest

from insurance_intelligence.evaluation.cross_provider_repeat_run import (
    CrossProviderRepeatRunError,
    build_cross_provider_repeat_run_evidence,
)


def _artifact(*, agreed: bool = True, matched: bool = True) -> dict[str, object]:
    component_ids = ("trigger", "effect")
    return {
        "run_type": "MO-022G_OPENAI_GEMINI_CROSS_PROVIDER",
        "data_classification": "PUBLIC",
        "certification_effect": "NONE",
        "certification_granted": False,
        "rule_family_preflight": {
            "family_id": "CONDITIONAL_COPAYMENT",
            "family_version": "1.0",
            "status": "PASSED",
        },
        "renderer_trace": {
            "model": "renderer-model",
            "prompt_version": "renderer-v1",
            "latency_ms": 10,
        },
        "openai_extractor_trace": {
            "model": "openai-model",
            "prompt_version": "openai-v1",
            "latency_ms": 20,
        },
        "gemini_extractor_trace": {
            "model": "gemini-model",
            "prompt_version": "gemini-v1",
            "latency_ms": 30,
        },
        "agreements": [
            {"component_id": item, "agreed": agreed} for item in component_ids
        ],
        "routing_result": {
            "decision": "HUMAN_REVIEW_REQUIRED",
            "reason_codes": ["RULE_FAMILY_NOT_CERTIFIED"],
        },
        "semantic_report": {
            "contract_id": "contract-1",
            "hard_failure_codes": [],
            "unresolved_component_ids": [],
            "comparisons": [
                {
                    "component_id": item,
                    "status": "MATCHED" if matched else "MISMATCHED",
                    "confidence": 0.9,
                }
                for item in component_ids
            ],
        },
    }


def test_cross_provider_repeat_run_marks_exact_batch_stable():
    evidence = build_cross_provider_repeat_run_evidence(
        [_artifact(), _artifact(), _artifact()], required_run_count=3
    )

    assert evidence.status == "CROSS_PROVIDER_SEMANTICALLY_STABLE"
    assert evidence.exact_agreement_every_run is True
    assert evidence.all_components_matched is True
    assert evidence.preflight_passed_every_run is True
    assert evidence.minimum_observed_confidence == 0.9
    assert evidence.certification_granted is False


def test_cross_provider_repeat_run_fails_closed_on_one_disagreement():
    evidence = build_cross_provider_repeat_run_evidence(
        [_artifact(), _artifact(agreed=False), _artifact()], required_run_count=3
    )

    assert evidence.status == "INSUFFICIENT_CROSS_PROVIDER_STABILITY"
    assert evidence.exact_agreement_every_run is False
    assert evidence.certification_effect == "NONE"


def test_cross_provider_repeat_run_rejects_tuple_drift():
    artifacts = [_artifact(), _artifact(), _artifact()]
    changed = deepcopy(artifacts[1])
    changed["gemini_extractor_trace"]["prompt_version"] = "gemini-v2"
    artifacts[1] = changed

    with pytest.raises(CrossProviderRepeatRunError, match="identical governed tuple"):
        build_cross_provider_repeat_run_evidence(artifacts, required_run_count=3)
