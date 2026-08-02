from __future__ import annotations

from copy import deepcopy

import pytest

from insurance_intelligence.evaluation.dual_extractor_repeat_run import (
    DualExtractorRepeatRunError,
    build_dual_extractor_repeat_run_evidence,
)


def _artifact(*, agreed: bool = True, matched: bool = True, confidence: float = 0.9):
    component_ids = ("entry-age-trigger", "copay-effect")
    return {
        "run_type": "MO-022G_DUAL_EXTRACTOR_LIVE_CERTIFICATION",
        "certification_effect": "NONE",
        "certification_granted": False,
        "renderer_trace": {"model": "renderer", "prompt_version": "renderer-v1"},
        "extractor_a_trace": {"model": "extractor", "prompt_version": "extractor-a-v1"},
        "extractor_b_trace": {"model": "extractor", "prompt_version": "extractor-b-v1"},
        "agreements": [
            {"component_id": component_id, "agreed": agreed}
            for component_id in component_ids
        ],
        "routing_result": {
            "decision": "HUMAN_REVIEW_REQUIRED",
            "reason_codes": ["RULE_FAMILY_NOT_CERTIFIED"],
        },
        "semantic_report": {
            "contract_id": "contract-v1",
            "hard_failure_codes": [],
            "unresolved_component_ids": [],
            "comparisons": [
                {
                    "component_id": component_id,
                    "status": "MATCHED" if matched else "UNRESOLVED",
                    "confidence": confidence,
                }
                for component_id in component_ids
            ],
        },
    }


def test_ready_when_every_run_agrees_and_matches():
    evidence = build_dual_extractor_repeat_run_evidence(
        [_artifact(), _artifact(), _artifact(confidence=0.95)],
        required_run_count=3,
    )
    assert evidence.status == "READY_FOR_CERTIFICATION_DECISION"
    assert evidence.exact_agreement_every_run is True
    assert evidence.all_components_matched is True
    assert evidence.minimum_observed_confidence == 0.9
    assert evidence.certification_granted is False
    assert evidence.certification_effect == "NONE"


def test_disagreement_is_insufficient():
    evidence = build_dual_extractor_repeat_run_evidence(
        [_artifact(), _artifact(agreed=False)],
        required_run_count=2,
    )
    assert evidence.status == "INSUFFICIENT_DUAL_EXTRACTOR_EVIDENCE"
    assert evidence.exact_agreement_every_run is False


def test_unresolved_is_insufficient():
    artifact = _artifact(matched=False)
    artifact["semantic_report"]["unresolved_component_ids"] = ["entry-age-trigger"]
    evidence = build_dual_extractor_repeat_run_evidence(
        [_artifact(), artifact],
        required_run_count=2,
    )
    assert evidence.status == "INSUFFICIENT_DUAL_EXTRACTOR_EVIDENCE"
    assert evidence.unresolved_free is False


def test_identity_drift_is_rejected():
    second = deepcopy(_artifact())
    second["extractor_b_trace"]["prompt_version"] = "extractor-b-v2"
    with pytest.raises(DualExtractorRepeatRunError, match="identical contract"):
        build_dual_extractor_repeat_run_evidence(
            [_artifact(), second],
            required_run_count=2,
        )


def test_certifying_artifact_is_rejected():
    second = _artifact()
    second["certification_granted"] = True
    with pytest.raises(DualExtractorRepeatRunError, match="no certification effect"):
        build_dual_extractor_repeat_run_evidence(
            [_artifact(), second],
            required_run_count=2,
        )
