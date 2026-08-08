from __future__ import annotations

import json
from pathlib import Path

from scripts.run_mo_022g_star_copay_certification_decision import (
    _load_repeat_evidence,
    main,
)


STAR_COMPONENT_IDS = [
    "entry-age-trigger",
    "copay-effect",
    "continuous-renewal-exception",
    "applicability-scope",
]


def _batch_payload() -> dict[str, object]:
    observation = {
        "run_index": 1,
        "artifact_sha256": "a" * 64,
        "routing_decision": "HUMAN_REVIEW_REQUIRED",
        "routing_reason_codes": ["LOW_EXTRACTION_CONFIDENCE", "RULE_FAMILY_NOT_CERTIFIED"],
        "agreed_component_ids": STAR_COMPONENT_IDS,
        "matched_component_ids": STAR_COMPONENT_IDS,
        "hard_failure_codes": [],
        "unresolved_component_ids": [],
        "minimum_confidence": 0.9,
        "renderer_latency_ms": 1,
        "openai_extractor_latency_ms": 2,
        "gemini_extractor_latency_ms": 3,
    }
    return {
        "stability_evidence": {
            "batch_id": "batch-1",
            "schema_version": "1.0",
            "contract_id": "contract-star-comprehensive-conditional-copay-v1",
            "rule_family_id": "CONDITIONAL_COPAYMENT",
            "rule_family_version": "1.0",
            "renderer_model": "renderer-model",
            "renderer_prompt_version": "renderer-v1",
            "openai_extractor_model": "openai-model",
            "openai_extractor_prompt_version": "openai-v1",
            "gemini_extractor_model": "gemini-model",
            "gemini_extractor_prompt_version": "gemini-v1",
            "data_classification": "PUBLIC",
            "required_run_count": 3,
            "completed_run_count": 3,
            "exact_agreement_every_run": True,
            "all_components_matched": True,
            "hard_failure_free": True,
            "unresolved_free": True,
            "preflight_passed_every_run": True,
            "minimum_observed_confidence": 0.9,
            "observations": [
                observation,
                {**observation, "run_index": 2, "artifact_sha256": "b" * 64},
                {**observation, "run_index": 3, "artifact_sha256": "c" * 64},
            ],
            "certification_effect": "NONE",
            "certification_granted": False,
            "status": "CROSS_PROVIDER_SEMANTICALLY_STABLE",
        }
    }


def test_load_repeat_evidence_reconstructs_observation_tuples(tmp_path: Path):
    source = tmp_path / "batch.json"
    source.write_text(json.dumps(_batch_payload()), encoding="utf-8")

    evidence = _load_repeat_evidence(source)

    assert evidence.minimum_observed_confidence == 0.9
    assert len(evidence.observations) == 3
    assert evidence.observations[0].agreed_component_ids == tuple(STAR_COMPONENT_IDS)


def test_main_writes_both_policy_views_with_coherence_and_without_provider_calls(monkeypatch, tmp_path: Path):
    source = tmp_path / "batch.json"
    output = tmp_path / "decision.json"
    source.write_text(json.dumps(_batch_payload()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_mo_022g_star_copay_certification_decision",
            "--input",
            str(source),
            "--output",
            str(output),
        ],
    )

    assert main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "2.0"
    assert payload["provider_calls_performed"] == 0
    assert payload["replay_source"] == "PERSISTED_REPEAT_RUN_EVIDENCE"
    assert payload["evidence_binding_status"] == "APPROVED"
    assert payload["human_decision"] == "APPROVE_FOR_CERTIFICATION_REVIEW"
    assert payload["coherence_result"]["status"] == "COHERENT"
    assert payload["coherence_result"]["failure_codes"] == []

    v1 = payload["decisions"]["v1_threshold_required"]
    assert v1["status"] == "REVIEW_ONLY"
    assert v1["reason_codes"] == ["MINIMUM_CONFIDENCE_NOT_MET"]
    assert v1["certification_granted"] is False

    v2 = payload["decisions"]["v2_deterministic_proof_primary"]
    assert v2["status"] == "CERTIFIED"
    assert v2["reason_codes"] == []
    assert v2["certification_granted"] is True
    assert v2["certification_effect"] == "GRANT"

    assert payload["decision"] == v1
    assert payload["policy"] == payload["policies"]["v1_threshold_required"]


def test_v2_remains_fail_closed_when_deterministic_proof_is_incomplete(monkeypatch, tmp_path: Path):
    payload = _batch_payload()
    payload["stability_evidence"]["all_components_matched"] = False
    source = tmp_path / "batch.json"
    output = tmp_path / "decision.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_mo_022g_star_copay_certification_decision",
            "--input",
            str(source),
            "--output",
            str(output),
        ],
    )

    assert main() == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    v2 = result["decisions"]["v2_deterministic_proof_primary"]

    assert v2["status"] == "REVIEW_ONLY"
    assert "CANONICAL_MATCH_NOT_PROVEN" in v2["reason_codes"]
    assert "MINIMUM_CONFIDENCE_NOT_MET" in v2["reason_codes"]
    assert v2["certification_granted"] is False


def test_v2_cannot_certify_when_repeat_evidence_cannot_prove_coherence(monkeypatch, tmp_path: Path):
    payload = _batch_payload()
    for observation in payload["stability_evidence"]["observations"]:
        observation["matched_component_ids"] = [
            component_id for component_id in STAR_COMPONENT_IDS
            if component_id != "continuous-renewal-exception"
        ]
    source = tmp_path / "batch.json"
    output = tmp_path / "decision.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_mo_022g_star_copay_certification_decision",
            "--input",
            str(source),
            "--output",
            str(output),
        ],
    )

    assert main() == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["coherence_result"]["status"] == "INCOMPLETE"
    assert "COHERENCE_PROOF_INCOMPLETE" in result["coherence_result"]["failure_codes"]
    v2 = result["decisions"]["v2_deterministic_proof_primary"]
    assert v2["status"] == "REVIEW_ONLY"
    assert "EXPLANATION_COHERENCE_NOT_PROVEN" in v2["reason_codes"]
    assert v2["certification_granted"] is False
