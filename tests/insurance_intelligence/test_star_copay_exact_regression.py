from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_mo_022g_star_copay_certification_decision import (
    _star_binding,
    main as certification_main,
)
from scripts.run_mo_022g_star_copay_live import build_star_copay_contract


FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "insurance_intelligence"
    / "star_comprehensive_conditional_copay_regression_v1.json"
)


def _case() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _normalized_value(value: object) -> object:
    return list(value) if isinstance(value, tuple) else value


def _contract_projection() -> dict[str, object]:
    contract = build_star_copay_contract()
    return {
        "contract_id": contract.contract_id,
        "contract_version": contract.contract_version,
        "rule_family": contract.rule_family,
        "approved_finding_ids": list(contract.approved_finding_ids),
        "prohibited_operations": list(contract.prohibited_operations),
        "components": [
            {
                "component_id": component.component_id,
                "kind": component.kind.value,
                "risk_tier": component.risk_tier.value,
                "required": component.required,
                "evidence_ids": list(component.evidence_ids),
                "attributes": {
                    attribute.name: _normalized_value(attribute.value)
                    for attribute in component.attributes
                },
            }
            for component in contract.components
        ],
    }


def _binding_projection() -> dict[str, object]:
    binding = _star_binding()
    return {
        "family_id": binding.family_id,
        "family_version": binding.family_version,
        "contract_id": binding.contract_id,
        "component_roles": [list(role) for role in binding.component_roles],
    }


def _repeat_payload(case: dict[str, object]) -> dict[str, object]:
    contract = case["contract"]
    certification = case["certification"]
    component_ids = [component["component_id"] for component in contract["components"]]
    observation = {
        "run_index": 1,
        "artifact_sha256": "a" * 64,
        "routing_decision": "HUMAN_REVIEW_REQUIRED",
        "routing_reason_codes": ["LOW_EXTRACTION_CONFIDENCE", "RULE_FAMILY_NOT_CERTIFIED"],
        "agreed_component_ids": component_ids,
        "matched_component_ids": component_ids,
        "hard_failure_codes": [],
        "unresolved_component_ids": [],
        "minimum_confidence": certification["minimum_observed_confidence"],
        "renderer_latency_ms": 1,
        "openai_extractor_latency_ms": 2,
        "gemini_extractor_latency_ms": 3,
    }
    return {
        "stability_evidence": {
            "batch_id": case["case_id"],
            "schema_version": "1.0",
            "contract_id": contract["contract_id"],
            "rule_family_id": contract["rule_family"],
            "rule_family_version": case["binding"]["family_version"],
            "renderer_model": "regression-renderer-model",
            "renderer_prompt_version": "regression-renderer-v1",
            "openai_extractor_model": "regression-openai-model",
            "openai_extractor_prompt_version": "regression-openai-v1",
            "gemini_extractor_model": "regression-gemini-model",
            "gemini_extractor_prompt_version": "regression-gemini-v1",
            "data_classification": "PUBLIC",
            "required_run_count": 3,
            "completed_run_count": 3,
            "exact_agreement_every_run": True,
            "all_components_matched": True,
            "hard_failure_free": True,
            "unresolved_free": True,
            "preflight_passed_every_run": True,
            "minimum_observed_confidence": certification["minimum_observed_confidence"],
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


def _run_replay(monkeypatch, tmp_path: Path, payload: dict[str, object]) -> dict[str, object]:
    source = tmp_path / "repeat-evidence.json"
    output = tmp_path / "certification-decision.json"
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
    assert certification_main() == 0
    return json.loads(output.read_text(encoding="utf-8"))


def test_star_copay_contract_matches_immutable_regression_oracle():
    case = _case()

    assert _contract_projection() == case["contract"]


def test_star_copay_binding_matches_immutable_regression_oracle():
    case = _case()

    assert _binding_projection() == case["binding"]


def test_star_copay_exact_case_keeps_expected_coherence_and_certification(monkeypatch, tmp_path: Path):
    case = _case()
    result = _run_replay(monkeypatch, tmp_path, _repeat_payload(case))
    expected = case["certification"]

    assert result["provider_calls_performed"] == 0
    assert result["coherence_result"]["status"] == expected["coherence_status"]
    assert result["coherence_result"]["failure_codes"] == expected["coherence_failure_codes"]

    v1 = result["decisions"]["v1_threshold_required"]
    expected_v1 = expected["v1_threshold_required"]
    assert v1["status"] == expected_v1["status"]
    assert v1["reason_codes"] == expected_v1["reason_codes"]
    assert v1["certification_granted"] is expected_v1["certification_granted"]

    v2 = result["decisions"]["v2_deterministic_proof_primary"]
    expected_v2 = expected["v2_deterministic_proof_primary"]
    assert v2["status"] == expected_v2["status"]
    assert v2["reason_codes"] == expected_v2["reason_codes"]
    assert v2["certification_granted"] is expected_v2["certification_granted"]
    assert v2["certification_effect"] == expected_v2["certification_effect"]


@pytest.mark.parametrize(
    "missing_component_id",
    [
        "entry-age-trigger",
        "copay-effect",
        "continuous-renewal-exception",
        "applicability-scope",
    ],
)
def test_star_copay_v2_fails_closed_if_any_required_semantic_component_is_unproven(
    monkeypatch,
    tmp_path: Path,
    missing_component_id: str,
):
    case = _case()
    payload = _repeat_payload(case)
    observations = payload["stability_evidence"]["observations"]
    for observation in observations:
        observation["matched_component_ids"] = [
            component_id
            for component_id in observation["matched_component_ids"]
            if component_id != missing_component_id
        ]

    result = _run_replay(monkeypatch, tmp_path, payload)
    expected = case["certification"]["missing_component"]

    assert result["coherence_result"]["status"] == expected["coherence_status"]
    assert expected["coherence_failure_code"] in result["coherence_result"]["failure_codes"]
    v2 = result["decisions"]["v2_deterministic_proof_primary"]
    assert v2["status"] == expected["v2_status"]
    assert expected["v2_reason_code"] in v2["reason_codes"]
    assert v2["certification_granted"] is expected["certification_granted"]
