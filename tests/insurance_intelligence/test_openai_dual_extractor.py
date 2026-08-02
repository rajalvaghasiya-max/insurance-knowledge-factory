import json

from insurance_intelligence.contracts.semantic_fidelity import FidelityRoutingDecision
from insurance_intelligence.llm.openai_component_locked import OpenAIComponentLockedProvider
from insurance_intelligence.llm.openai_dual_extractor import OpenAIDualExtractorProvider
from scripts.run_mo_022g_star_copay_live import build_live_policy, build_star_copay_contract


class _Response:
    def __init__(self, response_id, payload):
        self.status_code = 200
        self.text = ""
        self._payload = {
            "id": response_id,
            "output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(payload)}],
            }],
        }

    def json(self):
        return self._payload


def _rendered():
    return {
        "components": [
            {"component_id": "entry-age-trigger", "kind": "TRIGGER", "text": "Applies when the insured person is age 61 or older at entry."},
            {"component_id": "copay-effect", "kind": "EFFECT", "text": "A 10% copayment applies to each and every claim."},
            {"component_id": "continuous-renewal-exception", "kind": "EXCEPTION", "text": "Exception to the 10% copayment effect: if the insured was under 61 at entry and the policy renewed continuously with no break, the 10% copayment does not apply."},
            {"component_id": "applicability-scope", "kind": "APPLICABILITY_SCOPE", "text": "Applies exactly to sections II.1, II.2, II.3, II.4, II.5, II.6, II.7, II.8, II.9, II.10, II.11, II.15, and II.25."},
        ]
    }


def _attrs(**values):
    return [{"name": key, "value": value} for key, value in values.items()]


def _extracted(*, percentage=10):
    return {
        "components": [
            {"component_id": "entry-age-trigger", "kind": "TRIGGER", "reconstructed_attributes": _attrs(subject="insured_person", attribute="age_at_entry", operator=">=", value=61), "confidence": 0.99, "extractor_agreement": 0.11, "unresolved_reasons": []},
            {"component_id": "copay-effect", "kind": "EFFECT", "reconstructed_attributes": _attrs(effect_type="copayment", percentage=percentage, claim_scope="each_and_every_claim"), "confidence": 0.99, "extractor_agreement": 0.22, "unresolved_reasons": []},
            {"component_id": "continuous-renewal-exception", "kind": "EXCEPTION", "reconstructed_attributes": _attrs(age_operator="<", age_value=61, continuous_renewal=True, policy_break=False, logical_operator="AND"), "confidence": 0.99, "extractor_agreement": 0.33, "unresolved_reasons": []},
            {"component_id": "applicability-scope", "kind": "APPLICABILITY_SCOPE", "reconstructed_attributes": _attrs(mode="exact_set", sections=["II.1", "II.2", "II.3", "II.4", "II.5", "II.6", "II.7", "II.8", "II.9", "II.10", "II.11", "II.15", "II.25"]), "confidence": 0.99, "extractor_agreement": 0.44, "unresolved_reasons": []},
        ]
    }


def test_exact_dual_agreement_ignores_self_reported_agreement(monkeypatch):
    responses = iter([
        _Response("render", _rendered()),
        _Response("extract-a", _extracted()),
        _Response("extract-b", _extracted()),
    ])
    monkeypatch.setattr(
        "insurance_intelligence.llm.openai_component_locked.requests.post",
        lambda *args, **kwargs: next(responses),
    )
    provider = OpenAIDualExtractorProvider(
        provider=OpenAIComponentLockedProvider(api_key="test-key")
    )
    result = provider.evaluate(
        build_star_copay_contract(),
        audience="customer",
        reading_level="plain_language",
        policy=build_live_policy(),
        certification=None,
    )
    assert all(item.agreed for item in result.agreements)
    assert result.outcome.routing_result.decision is FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED
    assert "LOW_EXTRACTOR_AGREEMENT" not in result.outcome.routing_result.reason_codes
    assert "RULE_FAMILY_NOT_CERTIFIED" in result.outcome.routing_result.reason_codes


def test_dual_disagreement_routes_to_review(monkeypatch):
    responses = iter([
        _Response("render", _rendered()),
        _Response("extract-a", _extracted()),
        _Response("extract-b", _extracted(percentage=20)),
    ])
    monkeypatch.setattr(
        "insurance_intelligence.llm.openai_component_locked.requests.post",
        lambda *args, **kwargs: next(responses),
    )
    provider = OpenAIDualExtractorProvider(
        provider=OpenAIComponentLockedProvider(api_key="test-key")
    )
    result = provider.evaluate(
        build_star_copay_contract(),
        audience="customer",
        reading_level="plain_language",
        policy=build_live_policy(),
        certification=None,
    )
    disagreement = {item.component_id: item.agreed for item in result.agreements}
    assert disagreement["copay-effect"] is False
    assert result.outcome.routing_result.decision is FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED
    assert "LOW_EXTRACTOR_AGREEMENT" in result.outcome.routing_result.reason_codes
    assert "SEMANTIC_EXTRACTION_UNRESOLVED" in result.outcome.routing_result.reason_codes
