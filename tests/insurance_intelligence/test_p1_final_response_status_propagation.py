from insurance_intelligence.contracts.decision import build_output as build_decision_output
from insurance_intelligence.contracts.evidence import EvidencePackage, EvidenceResolverOutput, Lineage
from insurance_intelligence.contracts.explanation import build_input as build_explanation_input
from insurance_intelligence.contracts.reasoning import Finding, ReasoningEngineOutput
from insurance_intelligence.contracts.response import build_input as build_response_input
from insurance_intelligence.decision.aggregator import aggregate_decision
from insurance_intelligence.decision.evaluator import evaluate_finding
from insurance_intelligence.decision.registry import SafetyPolicyRegistry, build_policy_definition
from insurance_intelligence.explanation.generator import generate_explanation
from insurance_intelligence.explanation.registry import ExplanationStyleRegistry, build_style_definition
from insurance_intelligence.response.registry import ResponseFormatRegistry, build_format_definition
from insurance_intelligence.response.service import assemble_response


def _evidence() -> EvidencePackage:
    return EvidencePackage(
        evidence_id="ev-1",
        requirement_id="req-1",
        subject_reference="Star Comprehensive",
        governed_entity_reference="star_health:star_comprehensive",
        field_or_topic="documented_fact",
        claim="The governed policy wording supports this finding.",
        evidence_role="SUPPORTING",
        source_type="POLICY_WORDING",
        document_reference="doc-1",
        document_version="1.0",
        effective_from=None,
        effective_to=None,
        page=1,
        section="Policy wording",
        source_excerpt="Governed policy wording.",
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
        request_id="req-1",
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


def _finding(*, status: str, limitations=()) -> Finding:
    return Finding(
        finding_id="finding-1",
        requirement_id="req-1",
        finding_type="DOCUMENTED_FACT",
        subject="Star Comprehensive",
        predicate="documents",
        object_or_effect="the governed policy feature",
        condition=None,
        scope="product",
        finding_status=status,
        derivation_type="DIRECT_FACT",
        rule_id="direct_documented_fact_v1",
        rule_version="1.0",
        evidence_ids=("ev-1",),
        supporting_fact_ids=(),
        assumption_ids=(),
        limitations=tuple(limitations),
        confidence=0.9,
    )


def _reasoning_output(item: Finding) -> ReasoningEngineOutput:
    return ReasoningEngineOutput(
        contract_version="1.0",
        request_id="req-1",
        reasoning_id="reasoning-1",
        findings=(item,),
        requirement_results=(),
        rule_executions=(),
        unsupported_requirements=(),
        assumptions=(),
        limitations=(),
        reasoning_sufficiency="COMPLETE",
        reasoning_status="REASONED",
        confidence=0.9,
        reasoning_trace=(),
    )


def _decision(item: Finding, registry: SafetyPolicyRegistry):
    evaluation = evaluate_finding(
        finding=item,
        evidence_resolution=_evidence_output(),
        reasoning_output=_reasoning_output(item),
        policy_registry=registry,
        domain="health",
        topic="documented_fact",
        decision_context={},
    )
    aggregate = aggregate_decision(request_id="req-1", evaluations=(evaluation,))
    return build_decision_output(
        request_id="req-1",
        decision_id="decision-1",
        decision=aggregate.decision,
        finding_dispositions=aggregate.finding_dispositions,
        safety_issues=aggregate.safety_issues,
        clarifications=aggregate.clarifications,
        response_packet=aggregate.response_packet,
        blocked_content=aggregate.blocked_content,
        limitations=aggregate.limitations,
        human_review_reasons=aggregate.human_review_reasons,
        confidence=aggregate.confidence,
    )


def _styles() -> ExplanationStyleRegistry:
    return ExplanationStyleRegistry((
        build_style_definition(
            style_id="customer-simple-v1",
            style_version="1.0",
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_modes=("PLAIN_LANGUAGE",),
            max_section_words=120,
            priority=10,
        ),
    ))


def _response_registry() -> ResponseFormatRegistry:
    return ResponseFormatRegistry((
        build_format_definition(
            format_id="standard-answer-v1",
            format_version="1.0",
            response_format="STANDARD",
            audiences=("CUSTOMER",),
            response_statuses=("ANSWER", "ANSWER_WITH_LIMITATIONS"),
            section_order=("DIRECT_ANSWER", "EXPLANATION", "LIMITATION", "EVIDENCE"),
            allowed_section_types=("DIRECT_ANSWER", "EXPLANATION", "LIMITATION", "EVIDENCE"),
            direct_answer_policy="REQUIRED",
            evidence_policy="WHEN_AVAILABLE",
            limitation_policy="REQUIRED_WHEN_PRESENT",
            clarification_policy="FORBIDDEN",
            priority=10,
        ),
    ))


def _final_response(item: Finding, registry: SafetyPolicyRegistry):
    decision = _decision(item, registry)
    explanation = generate_explanation(
        explanation_input=build_explanation_input(
            request_id="req-1",
            decision_output=decision,
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_mode="PLAIN_LANGUAGE",
        ),
        findings_by_id={item.finding_id: item},
        style_registry=_styles(),
    )
    response = assemble_response(
        build_response_input(
            request_id="req-1",
            decision_output=decision,
            explanation_output=explanation,
            response_format="STANDARD",
        ),
        _response_registry(),
    )
    return decision, explanation, response


def test_partially_supported_status_reaches_final_response():
    item = _finding(
        status="PARTIALLY_SUPPORTED",
        limitations=("The approved evidence supports only part of this finding.",),
    )

    decision, explanation, response = _final_response(item, SafetyPolicyRegistry())

    assert decision.decision == "APPROVED_WITH_LIMITATIONS"
    assert explanation.explanation_status == "DRAFTED_WITH_LIMITATIONS"
    assert response.response_status == "ANSWER_WITH_LIMITATIONS"
    assert "partially supported" in response.direct_answer.lower()
    assert "The approved evidence supports only part of this finding." in response.limitations


def test_nonblocking_safety_warning_reaches_final_response_as_user_limitation():
    warning_policy = build_policy_definition(
        policy_id="p1_warning_policy_v1",
        policy_version="1.0",
        domain="health",
        topic="documented_fact",
        finding_types=("DOCUMENTED_FACT",),
        finding_statuses=("SUPPORTED",),
        derivation_types=("DIRECT_FACT",),
        reasoning_statuses=("REASONED",),
        reasoning_sufficiency_statuses=("COMPLETE",),
        evidence_resolution_statuses=("RESOLVED",),
        evidence_sufficiency_statuses=("COMPLETE",),
        strict_modes=("STRICT",),
        issue_type="POLICY_SPECIFIC_UNCERTAINTY",
        severity="LOW",
        finding_disposition="APPROVED_WITH_LIMITATIONS",
        decision_outcome="APPROVED_WITH_LIMITATIONS",
        blocking=False,
        evaluation_priority=1,
    )
    registry = SafetyPolicyRegistry((warning_policy,))

    decision, explanation, response = _final_response(_finding(status="SUPPORTED"), registry)

    assert decision.decision == "APPROVED_WITH_LIMITATIONS"
    assert explanation.explanation_status == "DRAFTED_WITH_LIMITATIONS"
    assert response.response_status == "ANSWER_WITH_LIMITATIONS"
    assert "Communicate only within the documented scope and conditions." in response.limitations

    user_visible = " ".join(
        filter(None, (response.direct_answer, *response.limitations, *(section.text for section in response.sections)))
    )
    assert "p1_warning_policy_v1" not in user_visible
