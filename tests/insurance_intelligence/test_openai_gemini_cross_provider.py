from __future__ import annotations

import json

from insurance_intelligence.contracts.semantic_fidelity import FidelityRoutingDecision
from insurance_intelligence.llm.gemini_semantic_extractor import GeminiSemanticExtractor
from insurance_intelligence.llm.openai_component_locked import OpenAIComponentLockedProvider
from insurance_intelligence.llm.openai_gemini_cross_provider import OpenAIGeminiCrossProvider
from scripts.run_mo_022g_star_copay_live import build_live_policy, build_star_copay_contract


class _Response:
    def __init__(self, response_id: str, payload: dict[str, object]):
        self.status_code = 200
        self._payload = {
            "id": response_id,
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": json.dumps(payload)}
                    ],
                }
            ],
        }
        self.text = json.dumps(self._payload)

    def json(self):
        return self._payload


class _GeminiResponse:
    status_code = 200
    text = "ok"

    def __init__(self, payload: dict[str, object]):
        self._payload = {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps(payload)}]}}
            ]
        }

    def json(self):
        return self._payload


def _rendered():
    return {
        "components": [
            {
                "component_id": "entry-age-trigger",
                "kind": "TRIGGER",
                "text": "Applies when the insured person is age 61 or older at entry.",
            },
            {
                "component_id": "copay-effect",
                "kind": "EFFECT",
                "text": "A 10% copayment applies to each and every claim.",
            },
            {
                "component_id": "continuous-renewal-exception",
                "kind": "EXCEPTION",
                "text": "Exception to the 10% copayment: if the insured was under 61 at entry and the policy has been continuously renewed with no break, the copayment does not apply.",
            },
            {
                "component_id": "applicability-scope",
                "kind": "APPLICABILITY_SCOPE",
                "text": "Applies exactly to sections II.1, II.2, II.3, II.4, II.5, II.6, II.7, II.8, II.9, II.10, II.11, II.15, and II.25.",
            },
        ]
    }


def _extracted(percentage: int = 10):
    return {
        "components": [
            {
                "component_id": "entry-age-trigger",
                "kind": "TRIGGER",
                "reconstructed_attributes": [
                    {"name": "attribute", "value": "age_at_entry"},
                    {"name": "operator", "value": ">="},
                    {"name": "subject", "value": "insured_person"},
                    {"name": "value", "value": 61},
                ],
                "confidence": 0.98,
                "extractor_agreement": 0.0,
                "unresolved_reasons": [],
            },
            {
                "component_id": "copay-effect",
                "kind": "EFFECT",
                "reconstructed_attributes": [
                    {"name": "claim_scope", "value": "each_and_every_claim"},
                    {"name": "effect_type", "value": "copayment"},
                    {"name": "percentage", "value": percentage},
                ],
                "confidence": 0.98,
                "extractor_agreement": 0.0,
                "unresolved_reasons": [],
            },
            {
                "component_id": "continuous-renewal-exception",
                "kind": "EXCEPTION",
                "reconstructed_attributes": [
                    {"name": "age_operator", "value": "<"},
                    {"name": "age_value", "value": 61},
                    {"name": "continuous_renewal", "value": True},
                    {"name": "logical_operator", "value": "AND"},
                    {"name": "policy_break", "value": False},
                ],
                "confidence": 0.98,
                "extractor_agreement": 0.0,
                "unresolved_reasons": [],
            },
            {
                "component_id": "applicability-scope",
                "kind": "APPLICABILITY_SCOPE",
                "reconstructed_attributes": [
                    {"name": "mode", "value": "exact_set"},
                    {
                        "name": "sections",
                        "value": [
                            "II.1",
                            "II.2",
                            "II.3",
                            "II.4",
                            "II.5",
                            "II.6",
                            "II.7",
                            "II.8",
                            "II.9",
                            "II.10",
                            "II.11",
                            "II.15",
                            "II.25",
                        ],
                    },
                ],
                "confidence": 0.98,
                "extractor_agreement": 0.0,
                "unresolved_reasons": [],
            },
        ]
    }


def _provider():
    return OpenAIGeminiCrossProvider(
        openai=OpenAIComponentLockedProvider(api_key="openai-test"),
        gemini=GeminiSemanticExtractor(api_key="gemini-test"),
    )


def _install_http_dispatch(monkeypatch, *, gemini_payload: dict[str, object]):
    openai_responses = iter(
        [_Response("render", _rendered()), _Response("extract", _extracted())]
    )

    def post(url, *args, **kwargs):
        if "generativelanguage.googleapis.com" in url:
            return _GeminiResponse(gemini_payload)
        if "api.openai.com" in url:
            return next(openai_responses)
        raise AssertionError(f"unexpected provider URL: {url}")

    monkeypatch.setattr(
        "insurance_intelligence.llm.openai_component_locked.requests.post",
        post,
    )


def test_cross_provider_exact_agreement(monkeypatch):
    _install_http_dispatch(monkeypatch, gemini_payload=_extracted())
    result = _provider().evaluate(
        build_star_copay_contract(),
        audience="customer",
        reading_level="plain_language",
        policy=build_live_policy(),
        certification=None,
        data_classification="PUBLIC",
    )
    assert all(item.agreed for item in result.agreements)
    assert all(
        item.status.value == "MATCHED"
        for item in result.outcome.fidelity_report.comparisons
    )
    assert (
        result.outcome.routing_result.decision
        is FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED
    )
    assert result.outcome.routing_result.reason_codes == (
        "RULE_FAMILY_NOT_CERTIFIED",
    )


def test_cross_provider_disagreement_fails_closed(monkeypatch):
    _install_http_dispatch(monkeypatch, gemini_payload=_extracted(percentage=20))
    result = _provider().evaluate(
        build_star_copay_contract(),
        audience="customer",
        reading_level="plain_language",
        policy=build_live_policy(),
        certification=None,
        data_classification="SYNTHETIC",
    )
    assert any(not item.agreed for item in result.agreements)
    reasons = result.outcome.routing_result.reason_codes
    assert "LOW_EXTRACTOR_AGREEMENT" in reasons
    assert "SEMANTIC_EXTRACTION_UNRESOLVED" in reasons
    assert "SEMANTIC_PROOF_INCOMPLETE" in reasons
