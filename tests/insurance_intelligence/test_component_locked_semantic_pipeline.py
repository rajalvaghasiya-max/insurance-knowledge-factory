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
from insurance_intelligence.llm.component_locked import (
    ComponentLockedRenderingError,
    build_component_locked_request,
    parse_component_locked_output,
)
from insurance_intelligence.llm.semantic_rendering_pipeline import (
    evaluate_component_locked_rendering,
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
                "entry-age-trigger",
                SemanticKind.TRIGGER,
                SemanticRiskTier.RULE_LOGIC,
                subject="insured_person",
                attribute="age_at_entry",
                operator=">=",
                value=61,
            ),
            _component(
                "copay-effect",
                SemanticKind.EFFECT,
                SemanticRiskTier.EXACT_VALUE,
                effect_type="copayment",
                percentage=10,
                claim_scope="each_and_every_claim",
            ),
            _component(
                "continuous-renewal-exception",
                SemanticKind.EXCEPTION,
                SemanticRiskTier.RULE_LOGIC,
                age_operator="<",
                age_value=61,
                continuous_renewal=True,
                policy_break=False,
                logical_operator="AND",
            ),
            _component(
                "applicability-scope",
                SemanticKind.APPLICABILITY_SCOPE,
                SemanticRiskTier.EXACT_VALUE,
                mode="exact_set",
                sections=SECTIONS,
            ),
        ),
        approved_finding_ids=("finding-star-copay",),
        prohibited_operations=(
            "ADD_FACT", "REMOVE_FACT", "INFER_FACT", "GENERALISE_SCOPE",
            "NARROW_SCOPE", "CHANGE_NUMBER", "CHANGE_OPERATOR", "CHANGE_CERTAINTY",
        ),
    )


@pytest.fixture
def request(contract):
    return build_component_locked_request(
        contract,
        audience="customer",
        reading_level="plain_language",
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
        prompt_version="component-locked-v1",
        extractor_policy_id="semantic-extractor-v1",
        status=CertificationStatus.CERTIFIED,
    )


def _attributes(**values):
    return [{"name": key, "value": value} for key, value in values.items()]


def _valid_payload(*, confidence=0.99, agreement=1.0, scope_sections=None):
    return {
        "components": [
            {
                "component_id": "entry-age-trigger",
                "kind": "TRIGGER",
                "text": "This applies when the insured person was 61 or older on joining.",
                "reconstructed_attributes": _attributes(
                    subject="insured_person", attribute="age_at_entry", operator=">=", value=61
                ),
                "confidence": confidence,
                "extractor_ids": ["extractor-a", "extractor-b"],
                "extractor_agreement": agreement,
                "unresolved_reasons": [],
            },
            {
                "component_id": "copay-effect",
                "kind": "EFFECT",
                "text": "The insured person pays 10% of every applicable claim.",
                "reconstructed_attributes": _attributes(
                    effect_type="copayment", percentage=10, claim_scope="each_and_every_claim"
                ),
                "confidence": confidence,
                "extractor_ids": ["extractor-a", "extractor-b"],
                "extractor_agreement": agreement,
                "unresolved_reasons": [],
            },
            {
                "component_id": "continuous-renewal-exception",
                "kind": "EXCEPTION",
                "text": "It does not apply if entry was before 61 and renewal continued without a break.",
                "reconstructed_attributes": _attributes(
                    age_operator="<", age_value=61, continuous_renewal=True,
                    policy_break=False, logical_operator="AND"
                ),
                "confidence": confidence,
                "extractor_ids": ["extractor-a", "extractor-b"],
                "extractor_agreement": agreement,
                "unresolved_reasons": [],
            },
            {
                "component_id": "applicability-scope",
                "kind": "APPLICABILITY_SCOPE",
                "text": "It applies only to the specified policy sections.",
                "reconstructed_attributes": _attributes(
                    mode="exact_set", sections=list(scope_sections or SECTIONS)
                ),
                "confidence": confidence,
                "extractor_ids": ["extractor-a", "extractor-b"],
                "extractor_agreement": agreement,
                "unresolved_reasons": [],
            },
        ]
    }


def test_request_locks_every_canonical_component(contract, request):
    assert request.contract_id == contract.contract_id
    assert tuple(item.component_id for item in request.instructions) == tuple(
        item.component_id for item in contract.components
    )
    assert "Return every component exactly once" in request.canonical_payload


def test_parser_requires_exact_component_coverage(request):
    payload = _valid_payload()
    payload["components"].pop()
    with pytest.raises(ComponentLockedRenderingError, match="exactly cover"):
        parse_component_locked_output(payload, request)


def test_parser_rejects_unknown_component(request):
    payload = _valid_payload()
    payload["components"][0]["component_id"] = "invented-component"
    with pytest.raises(ComponentLockedRenderingError, match="unknown component_id"):
        parse_component_locked_output(payload, request)


def test_exact_semantic_match_is_auto_approved_and_assembled(
    contract, request, policy, certification
):
    outcome = evaluate_component_locked_rendering(
        contract, request, _valid_payload(), policy, certification
    )
    assert outcome.routing_result.decision is FidelityRoutingDecision.AUTO_APPROVED
    assert outcome.verified_explanation is not None
    assert outcome.human_review_packet is None
    assert outcome.verified_explanation.combined_text.startswith("This applies when")
    assert "10%" in outcome.verified_explanation.combined_text


def test_non_contiguous_scope_expansion_is_auto_rejected(
    contract, request, policy, certification
):
    expanded = tuple(f"II.{value}" for value in range(1, 26))
    outcome = evaluate_component_locked_rendering(
        contract,
        request,
        _valid_payload(scope_sections=expanded),
        policy,
        certification,
    )
    assert outcome.routing_result.decision is FidelityRoutingDecision.AUTO_REJECTED
    assert "SEMANTIC_SET_MISMATCH" in outcome.routing_result.reason_codes
    assert outcome.verified_explanation is None
    assert outcome.human_review_packet is None


def test_changed_percentage_is_auto_rejected(contract, request, policy, certification):
    payload = _valid_payload()
    effect = next(item for item in payload["components"] if item["component_id"] == "copay-effect")
    effect["reconstructed_attributes"] = _attributes(
        effect_type="copayment", percentage=20, claim_scope="each_and_every_claim"
    )
    outcome = evaluate_component_locked_rendering(contract, request, payload, policy, certification)
    assert outcome.routing_result.decision is FidelityRoutingDecision.AUTO_REJECTED
    assert "EXACT_VALUE_CHANGED" in outcome.routing_result.reason_codes


def test_changed_operator_is_auto_rejected(contract, request, policy, certification):
    payload = _valid_payload()
    trigger = payload["components"][0]
    trigger["reconstructed_attributes"] = _attributes(
        subject="insured_person", attribute="age_at_entry", operator=">", value=61
    )
    outcome = evaluate_component_locked_rendering(contract, request, payload, policy, certification)
    assert outcome.routing_result.decision is FidelityRoutingDecision.AUTO_REJECTED
    assert "SEMANTIC_LOGIC_CHANGED" in outcome.routing_result.reason_codes


def test_low_confidence_routes_to_human_review(contract, request, policy, certification):
    outcome = evaluate_component_locked_rendering(
        contract, request, _valid_payload(confidence=0.90), policy, certification
    )
    assert outcome.routing_result.decision is FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED
    assert outcome.verified_explanation is None
    assert outcome.human_review_packet is not None
    assert "LOW_EXTRACTION_CONFIDENCE" in outcome.human_review_packet.reason_codes


def test_low_extractor_agreement_routes_to_review(contract, request, policy, certification):
    outcome = evaluate_component_locked_rendering(
        contract, request, _valid_payload(agreement=0.80), policy, certification
    )
    assert outcome.routing_result.decision is FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED
    assert "LOW_EXTRACTOR_AGREEMENT" in outcome.routing_result.reason_codes


def test_unresolved_semantics_route_to_review(contract, request, policy, certification):
    payload = _valid_payload()
    payload["components"][0]["unresolved_reasons"] = ["operator_ambiguous"]
    outcome = evaluate_component_locked_rendering(contract, request, payload, policy, certification)
    assert outcome.routing_result.decision is FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED
    assert "SEMANTIC_PROOF_INCOMPLETE" in outcome.routing_result.reason_codes
    assert "entry-age-trigger" in outcome.human_review_packet.component_ids


def test_uncertified_rule_family_routes_to_review(contract, request, policy):
    outcome = evaluate_component_locked_rendering(
        contract, request, _valid_payload(), policy, None
    )
    assert outcome.routing_result.decision is FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED
    assert "RULE_FAMILY_NOT_CERTIFIED" in outcome.routing_result.reason_codes
