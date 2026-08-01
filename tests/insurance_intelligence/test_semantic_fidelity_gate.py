import pytest

from insurance_intelligence.contracts.semantic_fidelity import (
    CanonicalSemanticComponent,
    CertificationStatus,
    ExplanationSemanticContract,
    FidelityRoutingDecision,
    FidelityRoutingPolicy,
    ReconstructedSemanticComponent,
    RuleFamilyCertification,
    SemanticAttribute,
    SemanticComparisonStatus,
    SemanticKind,
    SemanticRiskTier,
)
from insurance_intelligence.evaluation.semantic_fidelity import (
    SemanticFidelityError,
    build_human_review_packet,
    compare_semantics,
    route_fidelity_result,
)


def attribute(name, value):
    return SemanticAttribute(name=name, value=value)


def canonical(component_id, kind, risk, *attributes):
    return CanonicalSemanticComponent(
        component_id=component_id,
        kind=kind,
        risk_tier=risk,
        attributes=tuple(attributes),
        evidence_ids=("ev-star-copay-reviewed-statement",),
    )


def observed(component, *, confidence=0.99, agreement=1.0, unresolved=()):
    return ReconstructedSemanticComponent(
        component_id=component.component_id,
        kind=component.kind,
        attributes=component.attributes,
        confidence=confidence,
        extractor_ids=("extractor-a", "extractor-b"),
        extractor_agreement=agreement,
        unresolved_reasons=unresolved,
    )


@pytest.fixture
def contract():
    return ExplanationSemanticContract(
        contract_id="contract-star-copay-v1",
        contract_version="1.0.0",
        rule_family="CONDITIONAL_COPAYMENT",
        components=(
            canonical(
                "copay-rate",
                SemanticKind.FACT,
                SemanticRiskTier.EXACT_VALUE,
                attribute("type", "percentage"),
                attribute("value", 10),
            ),
            canonical(
                "entry-age-trigger",
                SemanticKind.TRIGGER,
                SemanticRiskTier.RULE_LOGIC,
                attribute("subject", "insured_person"),
                attribute("attribute", "age_at_entry"),
                attribute("operator", ">="),
                attribute("value", 61),
            ),
            canonical(
                "copay-effect",
                SemanticKind.EFFECT,
                SemanticRiskTier.RULE_LOGIC,
                attribute("type", "copayment"),
                attribute("claim_scope", "each_and_every_claim"),
            ),
            canonical(
                "pre-61-continuous-renewal",
                SemanticKind.EXCEPTION,
                SemanticRiskTier.RULE_LOGIC,
                attribute("age_at_entry_operator", "<"),
                attribute("age_at_entry_value", 61),
                attribute("continuous_renewal", True),
                attribute("policy_break", False),
            ),
            canonical(
                "applicability-scope",
                SemanticKind.APPLICABILITY_SCOPE,
                SemanticRiskTier.EXACT_VALUE,
                attribute("mode", "exact_set"),
                attribute(
                    "sections",
                    (
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
                    ),
                ),
            ),
        ),
        approved_finding_ids=("finding-star-copay",),
        prohibited_operations=(
            "ADD_FACT",
            "REMOVE_FACT",
            "CHANGE_SCOPE",
            "CHANGE_NUMBER",
            "CHANGE_LOGIC",
        ),
    )


@pytest.fixture
def policy():
    return FidelityRoutingPolicy(
        policy_id="semantic-routing-v1",
        minimum_confidence=0.97,
        minimum_extractor_agreement=1.0,
    )


@pytest.fixture
def certification():
    return RuleFamilyCertification(
        certification_id="cert-copay-v1",
        rule_family="CONDITIONAL_COPAYMENT",
        model_id="gpt-5-mini-2025-08-07",
        prompt_version="semantic-renderer-v1",
        extractor_policy_id="dual-extractor-v1",
        status=CertificationStatus.CERTIFIED,
    )


def test_exact_semantic_match_auto_approves(contract, policy, certification):
    reconstructed = tuple(observed(component) for component in contract.components)
    report = compare_semantics(contract, reconstructed)
    routing = route_fidelity_result(contract, report, policy, certification)

    assert report.hard_failure_codes == ()
    assert report.unresolved_component_ids == ()
    assert routing.decision is FidelityRoutingDecision.AUTO_APPROVED
    assert routing.reason_codes == ("SEMANTIC_FIDELITY_VERIFIED",)


def test_missing_required_component_auto_rejects(contract, policy, certification):
    reconstructed = tuple(observed(component) for component in contract.components[:-1])
    report = compare_semantics(contract, reconstructed)
    routing = route_fidelity_result(contract, report, policy, certification)

    assert "SEMANTIC_OMISSION" in report.hard_failure_codes
    assert routing.decision is FidelityRoutingDecision.AUTO_REJECTED


def test_new_component_auto_rejects(contract, policy, certification):
    extra = ReconstructedSemanticComponent(
        component_id="invented-benefit",
        kind=SemanticKind.FACT,
        attributes=(attribute("coverage", "worldwide"),),
        confidence=1.0,
        extractor_ids=("extractor-a",),
        extractor_agreement=1.0,
    )
    reconstructed = tuple(observed(component) for component in contract.components) + (extra,)
    report = compare_semantics(contract, reconstructed)
    routing = route_fidelity_result(contract, report, policy, certification)

    assert "UNSUPPORTED_SEMANTIC_ADDITION" in report.hard_failure_codes
    assert routing.decision is FidelityRoutingDecision.AUTO_REJECTED


def test_changed_percentage_auto_rejects(contract, policy, certification):
    reconstructed = list(observed(component) for component in contract.components)
    source = contract.components[0]
    reconstructed[0] = ReconstructedSemanticComponent(
        component_id=source.component_id,
        kind=source.kind,
        attributes=(attribute("type", "percentage"), attribute("value", 20)),
        confidence=1.0,
        extractor_ids=("extractor-a",),
        extractor_agreement=1.0,
    )
    report = compare_semantics(contract, tuple(reconstructed))

    assert "EXACT_VALUE_CHANGED" in report.hard_failure_codes


def test_changed_operator_auto_rejects(contract, policy, certification):
    reconstructed = list(observed(component) for component in contract.components)
    source = contract.components[1]
    reconstructed[1] = ReconstructedSemanticComponent(
        component_id=source.component_id,
        kind=source.kind,
        attributes=(
            attribute("subject", "insured_person"),
            attribute("attribute", "age_at_entry"),
            attribute("operator", ">"),
            attribute("value", 61),
        ),
        confidence=1.0,
        extractor_ids=("extractor-a",),
        extractor_agreement=1.0,
    )
    report = compare_semantics(contract, tuple(reconstructed))

    assert "SEMANTIC_LOGIC_CHANGED" in report.hard_failure_codes


def test_non_contiguous_scope_expansion_auto_rejects(contract, policy, certification):
    reconstructed = list(observed(component) for component in contract.components)
    source = contract.components[-1]
    reconstructed[-1] = ReconstructedSemanticComponent(
        component_id=source.component_id,
        kind=source.kind,
        attributes=(
            attribute("mode", "continuous_range"),
            attribute("sections", tuple(f"II.{index}" for index in range(1, 26))),
        ),
        confidence=1.0,
        extractor_ids=("extractor-a",),
        extractor_agreement=1.0,
    )
    report = compare_semantics(contract, tuple(reconstructed))

    assert "SEMANTIC_SET_MISMATCH" in report.hard_failure_codes
    assert "SEMANTIC_VALUE_CHANGED" in report.hard_failure_codes


def test_unresolved_extraction_routes_to_human_review(contract, policy, certification):
    reconstructed = list(observed(component) for component in contract.components)
    reconstructed[2] = observed(
        contract.components[2],
        confidence=0.80,
        agreement=0.50,
        unresolved=("ambiguous claim scope",),
    )
    report = compare_semantics(contract, tuple(reconstructed))
    routing = route_fidelity_result(contract, report, policy, certification)

    assert report.hard_failure_codes == ()
    assert report.unresolved_component_ids == ("copay-effect",)
    assert routing.decision is FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED
    assert routing.reason_codes == ("SEMANTIC_PROOF_INCOMPLETE",)


def test_low_confidence_match_routes_to_human_review(contract, policy, certification):
    reconstructed = tuple(
        observed(component, confidence=0.90 if component.component_id == "copay-effect" else 0.99)
        for component in contract.components
    )
    report = compare_semantics(contract, reconstructed)
    routing = route_fidelity_result(contract, report, policy, certification)

    assert report.hard_failure_codes == ()
    assert routing.decision is FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED
    assert "LOW_EXTRACTION_CONFIDENCE" in routing.reason_codes


def test_extractor_disagreement_routes_to_human_review(contract, policy, certification):
    reconstructed = tuple(
        observed(component, agreement=0.50 if component.component_id == "copay-effect" else 1.0)
        for component in contract.components
    )
    report = compare_semantics(contract, reconstructed)
    routing = route_fidelity_result(contract, report, policy, certification)

    assert routing.decision is FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED
    assert "LOW_EXTRACTOR_AGREEMENT" in routing.reason_codes


def test_uncertified_rule_family_routes_to_human_review(contract, policy):
    reconstructed = tuple(observed(component) for component in contract.components)
    report = compare_semantics(contract, reconstructed)
    routing = route_fidelity_result(contract, report, policy, None)

    assert routing.decision is FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED
    assert routing.reason_codes == ("RULE_FAMILY_NOT_CERTIFIED",)


def test_suspended_certification_routes_to_human_review(contract, policy, certification):
    suspended = RuleFamilyCertification(
        certification_id=certification.certification_id,
        rule_family=certification.rule_family,
        model_id=certification.model_id,
        prompt_version=certification.prompt_version,
        extractor_policy_id=certification.extractor_policy_id,
        status=CertificationStatus.SUSPENDED,
    )
    reconstructed = tuple(observed(component) for component in contract.components)
    report = compare_semantics(contract, reconstructed)
    routing = route_fidelity_result(contract, report, policy, suspended)

    assert routing.decision is FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED
    assert "RULE_FAMILY_NOT_CERTIFIED" in routing.reason_codes


def test_human_review_packet_contains_governed_evidence(contract, policy, certification):
    reconstructed = tuple(
        observed(component, confidence=0.90 if component.component_id == "copay-effect" else 0.99)
        for component in contract.components
    )
    report = compare_semantics(contract, reconstructed)
    routing = route_fidelity_result(contract, report, policy, certification)
    packet = build_human_review_packet(contract, report, routing)

    assert packet.contract_id == contract.contract_id
    assert "copay-effect" in packet.component_ids
    assert packet.evidence_ids == ("ev-star-copay-reviewed-statement",)


def test_review_packet_rejects_auto_approved_result(contract, policy, certification):
    reconstructed = tuple(observed(component) for component in contract.components)
    report = compare_semantics(contract, reconstructed)
    routing = route_fidelity_result(contract, report, policy, certification)

    with pytest.raises(SemanticFidelityError, match="HUMAN_REVIEW_REQUIRED"):
        build_human_review_packet(contract, report, routing)


def test_comparison_order_is_stable(contract):
    reconstructed = tuple(reversed(tuple(observed(component) for component in contract.components)))
    report = compare_semantics(contract, reconstructed)

    assert tuple(item.component_id for item in report.comparisons) == tuple(
        sorted(item.component_id for item in report.comparisons)
    )
    assert all(item.status is SemanticComparisonStatus.MATCHED for item in report.comparisons)
