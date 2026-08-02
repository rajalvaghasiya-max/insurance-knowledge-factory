import json

import pytest

from insurance_intelligence.contracts.semantic_fidelity import (
    CanonicalSemanticComponent,
    CertificationStatus,
    ExplanationSemanticContract,
    FidelityRoutingDecision,
    FidelityRoutingPolicy,
    RuleFamilyCertification,
    SemanticAttribute,
    SemanticKind,
    SemanticRiskTier,
)
from insurance_intelligence.llm.openai_component_locked import (
    OpenAIComponentLockedError,
    OpenAIComponentLockedProvider,
)


SECTIONS = (
    "II.1", "II.2", "II.3", "II.4", "II.5", "II.6", "II.7",
    "II.8", "II.9", "II.10", "II.11", "II.15", "II.25",
)


def _component(component_id, kind, risk_tier, **attributes):
    return CanonicalSemanticComponent(
        component_id=component_id,
        kind=kind,
        risk_tier=risk_tier,
        attributes=tuple(SemanticAttribute(name=k, value=v) for k, v in attributes.items()),
        evidence_ids=("ev-star-copay-reviewed-statement",),
    )


@pytest.fixture
def contract():
    return ExplanationSemanticContract(
        contract_id="contract-star-copay-v1",
        contract_version="1.0.0",
        rule_family="CONDITIONAL_COPAYMENT",
        components=(
            _component(
                "entry-age-trigger", SemanticKind.TRIGGER, SemanticRiskTier.RULE_LOGIC,
                subject="insured_person", attribute="age_at_entry", operator=">=", value=61,
            ),
            _component(
                "copay-effect", SemanticKind.EFFECT, SemanticRiskTier.EXACT_VALUE,
                effect_type="copayment", percentage=10, claim_scope="each_and_every_claim",
            ),
            _component(
                "continuous-renewal-exception", SemanticKind.EXCEPTION, SemanticRiskTier.RULE_LOGIC,
                age_operator="<", age_value=61, continuous_renewal=True,
                policy_break=False, logical_operator="AND",
            ),
            _component(
                "applicability-scope", SemanticKind.APPLICABILITY_SCOPE,
                SemanticRiskTier.EXACT_VALUE, mode="exact_set", sections=SECTIONS,
            ),
        ),
        approved_finding_ids=("finding-star-copay",),
        prohibited_operations=(
            "ADD_FACT", "REMOVE_FACT", "INFER_FACT", "GENERALISE_SCOPE",
            "NARROW_SCOPE", "CHANGE_NUMBER", "CHANGE_OPERATOR", "CHANGE_CERTAINTY",
        ),
    )


@pytest.fixture
def policy():
    return FidelityRoutingPolicy(
        policy_id="production-fidelity-v1",
        minimum_confidence=0.95,
        minimum_extractor_agreement=0.95,
    )


@pytest.fixture
def certification():
    return RuleFamilyCertification(
        certification_id="cert-conditional-copay-v1",
        rule_family="CONDITIONAL_COPAYMENT",
        model_id="gpt-5-mini-2025-08-07",
        prompt_version="component-locked-renderer-v1",
        extractor_policy_id="semantic-extractor-v1",
        status=CertificationStatus.CERTIFIED,
    )


def _rendered_payload():
    return {
        "components": [
            {"component_id": "entry-age-trigger", "kind": "TRIGGER", "text": "This applies when the insured person joined at age 61 or older."},
            {"component_id": "copay-effect", "kind": "EFFECT", "text": "The insured person pays 10% of every applicable claim."},
            {"component_id": "continuous-renewal-exception", "kind": "EXCEPTION", "text": "It does not apply if entry was before 61 and renewal continued without a break."},
            {"component_id": "applicability-scope", "kind": "APPLICABILITY_SCOPE", "text": "It applies only to the specified policy sections."},
        ]
    }


def _attrs(**values):
    return [{"name": key, "value": value} for key, value in values.items()]


def _extracted_payload(*, confidence=0.99, scope_sections=SECTIONS):
    return {
        "components": [
            {
                "component_id": "entry-age-trigger", "kind": "TRIGGER",
                "reconstructed_attributes": _attrs(subject="insured_person", attribute="age_at_entry", operator=">=", value=61),
                "confidence": confidence, "extractor_agreement": 1.0, "unresolved_reasons": [],
            },
            {
                "component_id": "copay-effect", "kind": "EFFECT",
                "reconstructed_attributes": _attrs(effect_type="copayment", percentage=10, claim_scope="each_and_every_claim"),
                "confidence": confidence, "extractor_agreement": 1.0, "unresolved_reasons": [],
            },
            {
                "component_id": "continuous-renewal-exception", "kind": "EXCEPTION",
                "reconstructed_attributes": _attrs(age_operator="<", age_value=61, continuous_renewal=True, policy_break=False, logical_operator="AND"),
                "confidence": confidence, "extractor_agreement": 1.0, "unresolved_reasons": [],
            },
            {
                "component_id": "applicability-scope", "kind": "APPLICABILITY_SCOPE",
                "reconstructed_attributes": _attrs(mode="exact_set", sections=list(scope_sections)),
                "confidence": confidence, "extractor_agreement": 1.0, "unresolved_reasons": [],
            },
        ]
    }


class _Response:
    def __init__(self, response_id, payload, status_code=200):
        self.status_code = status_code
        self.text = "error" if status_code >= 400 else ""
        self._payload = {
            "id": response_id,
            "output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(payload)}],
            }],
        }

    def json(self):
        return self._payload


def _provider():
    return OpenAIComponentLockedProvider(api_key="test-key")


def test_two_stage_provider_auto_approves_exact_semantics(monkeypatch, contract, policy, certification):
    responses = iter([
        _Response("resp-render", _rendered_payload()),
        _Response("resp-extract", _extracted_payload()),
    ])
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(kwargs["json"])
        return next(responses)

    monkeypatch.setattr("insurance_intelligence.llm.openai_component_locked.requests.post", fake_post)
    result = _provider().evaluate(
        contract, audience="customer", reading_level="plain_language",
        policy=policy, certification=certification,
    )

    assert len(calls) == 2
    assert calls[0]["text"]["format"]["type"] == "json_schema"
    assert calls[1]["text"]["format"]["strict"] is True
    assert result.rendering_trace.stage == "RENDERING"
    assert result.extraction_trace.stage == "EXTRACTION"
    assert result.outcome.routing_result.decision is FidelityRoutingDecision.AUTO_APPROVED
    assert result.outcome.verified_explanation is not None


def test_scope_expansion_is_rejected_after_extraction(monkeypatch, contract, policy, certification):
    expanded = tuple(f"II.{value}" for value in range(1, 26))
    responses = iter([
        _Response("resp-render", _rendered_payload()),
        _Response("resp-extract", _extracted_payload(scope_sections=expanded)),
    ])
    monkeypatch.setattr(
        "insurance_intelligence.llm.openai_component_locked.requests.post",
        lambda *args, **kwargs: next(responses),
    )
    result = _provider().evaluate(
        contract, audience="customer", reading_level="plain_language",
        policy=policy, certification=certification,
    )
    assert result.outcome.routing_result.decision is FidelityRoutingDecision.AUTO_REJECTED
    assert "SEMANTIC_SET_MISMATCH" in result.outcome.routing_result.reason_codes
    assert result.outcome.verified_explanation is None


def test_low_extraction_confidence_routes_to_human_review(monkeypatch, contract, policy, certification):
    responses = iter([
        _Response("resp-render", _rendered_payload()),
        _Response("resp-extract", _extracted_payload(confidence=0.80)),
    ])
    monkeypatch.setattr(
        "insurance_intelligence.llm.openai_component_locked.requests.post",
        lambda *args, **kwargs: next(responses),
    )
    result = _provider().evaluate(
        contract, audience="customer", reading_level="plain_language",
        policy=policy, certification=certification,
    )
    assert result.outcome.routing_result.decision is FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED
    assert result.outcome.human_review_packet is not None


def test_provider_http_error_fails_closed(monkeypatch, contract, policy, certification):
    monkeypatch.setattr(
        "insurance_intelligence.llm.openai_component_locked.requests.post",
        lambda *args, **kwargs: _Response("resp-error", {}, status_code=429),
    )
    with pytest.raises(OpenAIComponentLockedError, match="HTTP 429"):
        _provider().evaluate(
            contract, audience="customer", reading_level="plain_language",
            policy=policy, certification=certification,
        )
