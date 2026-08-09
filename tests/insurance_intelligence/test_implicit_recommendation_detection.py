from __future__ import annotations

import pytest

from insurance_intelligence.contracts.decision import (
    build_approved_response_packet,
    build_finding_disposition,
    build_output as build_decision_output,
)
from insurance_intelligence.contracts.evidence import EvidencePackage, EvidenceResolverOutput, Lineage
from insurance_intelligence.contracts.explanation import build_input, build_section
from insurance_intelligence.contracts.reasoning import Finding, ReasoningEngineOutput, build_finding
from insurance_intelligence.decision.evaluator import evaluate_finding
from insurance_intelligence.decision.registry import SafetyPolicyRegistry
from insurance_intelligence.explanation.validator import validate_explanation_fidelity


def _evidence() -> EvidencePackage:
    return EvidencePackage(
        evidence_id="ev-1",
        requirement_id="req-1",
        subject_reference="Star Comprehensive",
        governed_entity_reference="star_health:star_comprehensive",
        field_or_topic="product_comparison",
        claim="The governed product facts can be compared without choosing a product.",
        evidence_role="SUPPORTING",
        source_type="POLICY_WORDING",
        document_reference="doc-1",
        document_version="1.0",
        effective_from=None,
        effective_to=None,
        page=1,
        section="Comparison",
        source_excerpt="Governed comparison facts.",
        normalized_fact_reference="fact-1",
        authority_rank=1,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=Lineage(
            "source.pdf",
            "a" * 64,
            "binding.json",
            "b" * 64,
            "binding-1",
            "projection-1",
            "VERIFIED",
        ),
        retrieval_basis=("binding",),
        confidence=1.0,
    )


def _evidence_output() -> EvidenceResolverOutput:
    return EvidenceResolverOutput(
        contract_version="1.0",
        request_id="req",
        resolution_id="resolution-1",
        evidence_packages=(_evidence(),),
        requirement_results=(),
        entity_resolutions=(),
        document_resolutions=(),
        conflicts=(),
        missing_evidence=(),
        sufficiency="COMPLETE",
        limitations=(),
        resolution_trace=(),
        resolution_status="RESOLVED",
        confidence=1.0,
    )


def _finding() -> Finding:
    return build_finding(
        finding_id="finding-1",
        requirement_id="req-1",
        finding_type="DOCUMENTED_FACT",
        subject="Plan A",
        predicate="has",
        object_or_effect="the documented comparison feature",
        scope="product comparison",
        finding_status="SUPPORTED",
        derivation_type="DIRECT_FACT",
        rule_id="direct_documented_fact_v1",
        rule_version="1.0",
        evidence_ids=("ev-1",),
        confidence=0.95,
    )


def _reasoning_output(item: Finding) -> ReasoningEngineOutput:
    return ReasoningEngineOutput(
        contract_version="1.0",
        request_id="req",
        reasoning_id="reasoning-1",
        findings=(item,),
        requirement_results=(),
        rule_executions=(),
        unsupported_requirements=(),
        assumptions=(),
        limitations=(),
        reasoning_sufficiency="COMPLETE",
        reasoning_status="REASONED",
        confidence=0.95,
        reasoning_trace=(),
    )


def _evaluate_operation(operation: str):
    item = _finding()
    return evaluate_finding(
        finding=item,
        evidence_resolution=_evidence_output(),
        reasoning_output=_reasoning_output(item),
        policy_registry=SafetyPolicyRegistry(),
        domain="health",
        topic="documented_fact",
        decision_context={},
        requested_operations=(operation,),
    )


@pytest.mark.parametrize(
    "operation",
    (
        "RANK_PRODUCTS",
        "SELECT_PRODUCT",
        "PREFER_PLAN",
        "BEST_FIT_OPTION",
        "recommend-coverage",
        "assess suitability",
    ),
)
def test_implicit_recommendation_operations_are_blocked(operation):
    result = _evaluate_operation(operation)
    assert result.finding_disposition.disposition == "BLOCKED"
    assert any(
        issue.issue_type == "RECOMMENDATION_WITHOUT_SUITABILITY" and issue.blocking
        for issue in result.safety_issues
    )


def test_plain_product_comparison_remains_allowed():
    result = _evaluate_operation("COMPARE_PRODUCTS")
    assert result.finding_disposition.disposition == "APPROVED"
    assert not any(
        issue.issue_type == "RECOMMENDATION_WITHOUT_SUITABILITY"
        for issue in result.safety_issues
    )


def _decision():
    packet = build_approved_response_packet(
        packet_id="packet-1",
        approved_finding_ids=("finding-1",),
        approved_evidence_ids=("ev-1",),
        prohibited_operations=("RECOMMEND",),
    )
    disposition = build_finding_disposition(
        finding_id="finding-1",
        disposition="APPROVED",
        basis="Approved only for recommendation-language fidelity regression.",
        approved_evidence_ids=("ev-1",),
        confidence=0.95,
    )
    return build_decision_output(
        request_id="req",
        decision_id="decision-1",
        decision="APPROVED",
        finding_dispositions=(disposition,),
        response_packet=packet,
        confidence=0.95,
    )


def _validate_text(text: str):
    finding = _finding()
    explanation_input = build_input(
        request_id="req",
        decision_output=_decision(),
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_mode="PLAIN_LANGUAGE",
    )
    section = build_section(
        section_id="section-1",
        section_type="MEANING",
        status="DRAFTED",
        text=text,
        approved_finding_ids=("finding-1",),
        evidence_ids=("ev-1",),
    )
    return validate_explanation_fidelity(
        explanation_input=explanation_input,
        sections=(section,),
        findings_by_id={"finding-1": finding},
    )


@pytest.mark.parametrize(
    "text",
    (
        "You'd be better off with Plan A.",
        "Plan A fits your needs best.",
        "Plan A is the right choice for you.",
        "I would go with Plan A.",
        "Plan A is the more suitable plan for your needs.",
    ),
)
def test_implicit_recommendation_language_fails_fidelity(text):
    result = _validate_text(text)
    assert result.fidelity_status == "FAILED"
    assert result.validation_status == "FAILED_UNSUPPORTED_CONTENT"
    no_recommendation = next(check for check in result.checks if check.check_type == "NO_RECOMMENDATION")
    assert no_recommendation.status == "FAILED"


def test_neutral_comparison_language_passes_recommendation_check():
    result = _validate_text("Plan A has the documented comparison feature.")
    no_recommendation = next(check for check in result.checks if check.check_type == "NO_RECOMMENDATION")
    assert no_recommendation.status == "PASSED"
