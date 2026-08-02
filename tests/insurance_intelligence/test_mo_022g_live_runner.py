from __future__ import annotations

import json

from insurance_intelligence.contracts.semantic_fidelity import FidelityRoutingDecision
from insurance_intelligence.llm.component_locked import build_component_locked_request
from insurance_intelligence.llm.openai_component_locked import (
    OpenAIComponentLockedResult,
    OpenAIStageTrace,
)
from insurance_intelligence.llm.semantic_rendering_pipeline import (
    evaluate_component_locked_rendering,
)
from scripts.run_mo_022g_star_copay_live import (
    SECTIONS,
    build_live_policy,
    build_star_copay_contract,
    result_payload,
    write_result,
)


def _attributes(**values):
    return [{"name": key, "value": value} for key, value in values.items()]


def _valid_output():
    return {
        "components": [
            {
                "component_id": "entry-age-trigger",
                "kind": "TRIGGER",
                "text": "This applies when the insured person was 61 or older on joining.",
                "reconstructed_attributes": _attributes(
                    subject="insured_person",
                    attribute="age_at_entry",
                    operator=">=",
                    value=61,
                ),
                "confidence": 0.99,
                "extractor_ids": ["semantic-extractor-v1"],
                "extractor_agreement": 1.0,
                "unresolved_reasons": [],
            },
            {
                "component_id": "copay-effect",
                "kind": "EFFECT",
                "text": "The insured person pays 10% of every applicable claim.",
                "reconstructed_attributes": _attributes(
                    effect_type="copayment",
                    percentage=10,
                    claim_scope="each_and_every_claim",
                ),
                "confidence": 0.99,
                "extractor_ids": ["semantic-extractor-v1"],
                "extractor_agreement": 1.0,
                "unresolved_reasons": [],
            },
            {
                "component_id": "continuous-renewal-exception",
                "kind": "EXCEPTION",
                "text": "It does not apply when entry was before 61 and renewal continued without a break.",
                "reconstructed_attributes": _attributes(
                    age_operator="<",
                    age_value=61,
                    continuous_renewal=True,
                    policy_break=False,
                    logical_operator="AND",
                ),
                "confidence": 0.99,
                "extractor_ids": ["semantic-extractor-v1"],
                "extractor_agreement": 1.0,
                "unresolved_reasons": [],
            },
            {
                "component_id": "applicability-scope",
                "kind": "APPLICABILITY_SCOPE",
                "text": "It applies only to the listed policy sections.",
                "reconstructed_attributes": _attributes(
                    mode="exact_set",
                    sections=list(SECTIONS),
                ),
                "confidence": 0.99,
                "extractor_ids": ["semantic-extractor-v1"],
                "extractor_agreement": 1.0,
                "unresolved_reasons": [],
            },
        ]
    }


def test_live_contract_uses_exact_non_contiguous_scope():
    contract = build_star_copay_contract()
    scope = next(item for item in contract.components if item.component_id == "applicability-scope")
    values = {item.name: item.value for item in scope.attributes}

    assert values["mode"] == "exact_set"
    assert values["sections"] == SECTIONS
    assert "II.12" not in values["sections"]
    assert "II.25" in values["sections"]


def test_live_policy_cannot_auto_approve_without_certification():
    contract = build_star_copay_contract()
    request = build_component_locked_request(
        contract,
        audience="customer",
        reading_level="plain_language",
    )
    outcome = evaluate_component_locked_rendering(
        contract,
        request,
        _valid_output(),
        build_live_policy(),
        certification=None,
    )

    assert outcome.routing_result.decision is FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED
    assert outcome.routing_result.reason_codes == ("RULE_FAMILY_NOT_CERTIFIED",)
    assert outcome.verified_explanation is None
    assert outcome.human_review_packet is not None


def test_live_payload_records_no_certification_effect(tmp_path):
    contract = build_star_copay_contract()
    request = build_component_locked_request(
        contract,
        audience="customer",
        reading_level="plain_language",
    )
    outcome = evaluate_component_locked_rendering(
        contract,
        request,
        _valid_output(),
        build_live_policy(),
        certification=None,
    )
    trace = OpenAIStageTrace(
        trace_id="trace-render",
        stage="RENDERING",
        model="test-model",
        prompt_version="component-locked-renderer-v1",
        request_id=request.request_id,
        provider_response_id="response-render",
        latency_ms=10,
        canonical_output="{}",
    )
    extraction_trace = OpenAIStageTrace(
        trace_id="trace-extract",
        stage="EXTRACTION",
        model="test-model",
        prompt_version="semantic-extractor-v1",
        request_id=request.request_id,
        provider_response_id="response-extract",
        latency_ms=20,
        canonical_output="{}",
    )
    payload = result_payload(
        OpenAIComponentLockedResult(
            rendering_trace=trace,
            extraction_trace=extraction_trace,
            outcome=outcome,
        )
    )
    target = tmp_path / "live.json"
    write_result(target, payload)
    saved = json.loads(target.read_text(encoding="utf-8"))

    assert saved["certification_effect"] == "NONE"
    assert saved["routing_result"]["decision"] == "HUMAN_REVIEW_REQUIRED"
    assert saved["human_review_packet"] is not None
    assert saved["verified_explanation"] is None
    assert saved["renderer_trace"]["stage"] == "RENDERING"
    assert saved["extractor_trace"]["stage"] == "EXTRACTION"
