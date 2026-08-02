import copy

import pytest

from insurance_intelligence.evaluation.repeat_run_certification import (
    RepeatRunCertificationError,
    build_repeat_run_evidence,
)


def _artifact(*, confidence=0.95, hard_failures=None, unresolved=None, status="MATCHED"):
    comparisons = [
        {
            "component_id": component_id,
            "status": status,
            "confidence": confidence,
            "extractor_agreement": 1.0,
        }
        for component_id in (
            "entry-age-trigger",
            "copay-effect",
            "continuous-renewal-exception",
            "applicability-scope",
        )
    ]
    return {
        "run_type": "MO-022G_CONTROLLED_LIVE_CERTIFICATION",
        "certification_effect": "NONE",
        "renderer_trace": {
            "model": "gpt-5-mini-2025-08-07",
            "prompt_version": "component-locked-renderer-v2",
        },
        "extractor_trace": {
            "model": "gpt-5-mini-2025-08-07",
            "prompt_version": "semantic-extractor-v3",
        },
        "routing_result": {
            "decision": "HUMAN_REVIEW_REQUIRED",
            "reason_codes": ["RULE_FAMILY_NOT_CERTIFIED"],
        },
        "semantic_report": {
            "contract_id": "contract-star-comprehensive-conditional-copay-v1",
            "comparisons": comparisons,
            "hard_failure_codes": hard_failures or [],
            "unresolved_component_ids": unresolved or [],
        },
    }


def test_repeat_run_evidence_is_ready_but_never_certifies():
    evidence = build_repeat_run_evidence(
        [_artifact(confidence=0.95), _artifact(confidence=0.9), _artifact(confidence=0.97)],
        required_run_count=3,
    )
    assert evidence.status == "READY_FOR_CERTIFICATION_DECISION"
    assert evidence.semantically_consistent is True
    assert evidence.all_components_matched is True
    assert evidence.hard_failure_free is True
    assert evidence.unresolved_free is True
    assert evidence.minimum_observed_confidence == 0.9
    assert evidence.certification_effect == "NONE"
    assert evidence.certification_granted is False


def test_hard_failure_makes_repeat_evidence_insufficient():
    evidence = build_repeat_run_evidence(
        [_artifact(), _artifact(hard_failures=["SEMANTIC_VALUE_CHANGED"])],
        required_run_count=2,
    )
    assert evidence.status == "INSUFFICIENT_REPEAT_RUN_EVIDENCE"
    assert evidence.hard_failure_free is False


def test_unresolved_component_makes_repeat_evidence_insufficient():
    evidence = build_repeat_run_evidence(
        [_artifact(), _artifact(unresolved=["continuous-renewal-exception"])],
        required_run_count=2,
    )
    assert evidence.status == "INSUFFICIENT_REPEAT_RUN_EVIDENCE"
    assert evidence.unresolved_free is False


def test_mixed_contract_or_prompt_is_rejected():
    changed = copy.deepcopy(_artifact())
    changed["extractor_trace"]["prompt_version"] = "semantic-extractor-v4"
    with pytest.raises(RepeatRunCertificationError, match="same contract, models, and prompts"):
        build_repeat_run_evidence([_artifact(), changed], required_run_count=2)


def test_required_run_count_must_match_artifacts():
    with pytest.raises(RepeatRunCertificationError, match="artifact count"):
        build_repeat_run_evidence([_artifact(), _artifact()], required_run_count=3)
