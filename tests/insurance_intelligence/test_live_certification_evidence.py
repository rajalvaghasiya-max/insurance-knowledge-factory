import copy

import pytest

from insurance_intelligence.evaluation.live_certification_evidence import (
    LiveCertificationEvidenceError,
    build_governed_live_evidence,
)


def _artifact():
    comparisons = []
    for component_id, confidence in (
        ("entry-age-trigger", 0.95),
        ("copay-effect", 0.95),
        ("continuous-renewal-exception", 0.90),
        ("applicability-scope", 0.95),
    ):
        comparisons.append(
            {
                "component_id": component_id,
                "status": "MATCHED",
                "confidence": confidence,
                "extractor_agreement": 1.0,
                "mismatch_codes": [],
            }
        )
    return {
        "run_type": "MO-022G_CONTROLLED_LIVE_CERTIFICATION",
        "certification_effect": "NONE",
        "renderer_trace": {
            "model": "gpt-5-mini-2025-08-07",
            "prompt_version": "component-locked-renderer-v2",
            "canonical_output": "raw-renderer-output-must-not-be-projected",
        },
        "extractor_trace": {
            "model": "gpt-5-mini-2025-08-07",
            "prompt_version": "semantic-extractor-v3",
            "canonical_output": "raw-extractor-output-must-not-be-projected",
        },
        "routing_result": {
            "decision": "HUMAN_REVIEW_REQUIRED",
            "reason_codes": [
                "LOW_EXTRACTION_CONFIDENCE",
                "RULE_FAMILY_NOT_CERTIFIED",
            ],
        },
        "semantic_report": {
            "contract_id": "contract-star-comprehensive-conditional-copay-v1",
            "hard_failure_codes": [],
            "unresolved_component_ids": [],
            "comparisons": comparisons,
        },
    }


def test_projects_compact_non_certifying_evidence_without_raw_outputs():
    evidence = build_governed_live_evidence(_artifact())
    payload = evidence.to_dict()

    assert evidence.routing_decision == "HUMAN_REVIEW_REQUIRED"
    assert evidence.hard_failure_codes == ()
    assert evidence.certification_granted is False
    assert evidence.reviewer_decision == "PENDING"
    assert [item.component_id for item in evidence.components] == sorted(
        item.component_id for item in evidence.components
    )
    assert "canonical_output" not in payload
    assert "raw-renderer-output" not in str(payload)
    assert "raw-extractor-output" not in str(payload)


def test_projection_is_deterministic_for_identical_artifact():
    first = build_governed_live_evidence(_artifact())
    second = build_governed_live_evidence(copy.deepcopy(_artifact()))

    assert first.evidence_id == second.evidence_id
    assert first.source_artifact_sha256 == second.source_artifact_sha256


def test_projection_rejects_any_attempt_to_grant_certification():
    artifact = _artifact()
    artifact["certification_effect"] = "GRANTED"

    with pytest.raises(LiveCertificationEvidenceError, match="cannot grant certification"):
        build_governed_live_evidence(artifact)


def test_projection_preserves_mismatch_as_evidence_not_approval():
    artifact = _artifact()
    artifact["semantic_report"]["comparisons"][0]["status"] = "MISMATCHED"
    artifact["semantic_report"]["comparisons"][0]["mismatch_codes"] = [
        "SEMANTIC_VALUE_CHANGED"
    ]
    artifact["semantic_report"]["hard_failure_codes"] = ["SEMANTIC_VALUE_CHANGED"]
    artifact["routing_result"]["decision"] = "AUTO_REJECTED"

    evidence = build_governed_live_evidence(artifact)

    assert evidence.routing_decision == "AUTO_REJECTED"
    assert evidence.hard_failure_codes == ("SEMANTIC_VALUE_CHANGED",)
    assert evidence.certification_granted is False
