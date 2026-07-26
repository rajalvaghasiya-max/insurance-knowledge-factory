from __future__ import annotations

from dataclasses import replace

import pytest

from insurance_intelligence.contracts.evidence import (
    EvidenceConflict,
    EvidencePackage,
    EvidenceResolverOutput,
    Lineage,
)
from insurance_intelligence.contracts.reasoning import (
    Finding,
    ReasoningEngineOutput,
)
from insurance_intelligence.decision.evaluator import (
    FindingSafetyEvaluationError,
    evaluate_finding,
)
from insurance_intelligence.decision.registry import SafetyPolicyRegistry, build_policy_definition


def evidence(evidence_id="ev-1", *, lineage_status="VERIFIED", version_status="CURRENT_APPLICABLE", applicability_status="APPLICABLE"):
    return EvidencePackage(
        evidence_id=evidence_id,
        requirement_id="req-1",
        subject_reference="Star Comprehensive",
        governed_entity_reference="star_health:star_comprehensive",
        field_or_topic="conditional_copayment",
        claim="A 10% co-payment applies when the documented trigger applies.",
        evidence_role="SUPPORTING",
        source_type="POLICY_WORDING",
        document_reference="doc-1",
        document_version="1.0",
        effective_from=None,
        effective_to=None,
        page=39,
        section="Co-payment",
        source_excerpt="10% co-payment",
        normalized_fact_reference="fact-1",
        authority_rank=1,
        authority_requirement="BINDING",
        version_status=version_status,
        applicability_status=applicability_status,
        lineage=Lineage("source.pdf", "a" * 64, "binding.json", "b" * 64, "binding-1", "projection-1", lineage_status),
        retrieval_basis=("binding",),
        confidence=1.0,
    )


def evidence_output(*, packages=None, sufficiency="COMPLETE", resolution_status="RESOLVED", conflicts=()):
    return EvidenceResolverOutput(
        contract_version="1.0",
        request_id="req",
        resolution_id="resolution-1",
        evidence_packages=tuple(packages if packages is not None else (evidence(),)),
        requirement_results=(),
        entity_resolutions=(),
        document_resolutions=(),
        conflicts=tuple(conflicts),
        missing_evidence=(),
        sufficiency=sufficiency,
        limitations=(),
        resolution_trace=(),
        resolution_status=resolution_status,
        confidence=1.0,
    )


def finding(**overrides):
    values = dict(
        finding_id="finding-1",
        requirement_id="req-1",
        finding_type="CLAIM_COST_SHARING",
        subject="insured",
        predicate="must_bear",
        object_or_effect="10% of admissible claim amount",
        condition="documented trigger applies",
        scope="general clause meaning",
        finding_status="SUPPORTED",
        derivation_type="CONDITIONAL_DERIVATION",
        rule_id="conditional_copayment_obligation_v1",
        rule_version="1.0",
        evidence_ids=("ev-1",),
        supporting_fact_ids=(),
        assumption_ids=(),
        limitations=(),
        confidence=0.95,
    )
    values.update(overrides)
    return Finding(**values)


def reasoning_output(item=None, **overrides):
    item = item or finding()
    values = dict(
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
    values.update(overrides)
    return ReasoningEngineOutput(**values)


def evaluate(item=None, *, ev=None, ro=None, registry=None, context=None, operations=(), topic="conditional_copayment"):
    item = item or finding()
    ro = ro or reasoning_output(item)
    return evaluate_finding(
        finding=item,
        evidence_resolution=ev or evidence_output(),
        reasoning_output=ro,
        policy_registry=registry or SafetyPolicyRegistry(),
        domain="health",
        topic=topic,
        decision_context=context or {},
        requested_operations=operations,
    )


def test_supported_finding_is_approved_with_evidence_preserved():
    result = evaluate()
    assert result.finding_disposition.disposition == "APPROVED"
    assert result.finding_disposition.approved_evidence_ids == ("ev-1",)
    assert result.safety_issues == ()


def test_supported_with_limitations_is_approved_with_limitations():
    item = finding(finding_status="SUPPORTED_WITH_LIMITATIONS", limitations=("Policy-specific schedule may override.",))
    result = evaluate(item)
    assert result.finding_disposition.disposition == "APPROVED_WITH_LIMITATIONS"
    assert result.limitations
    assert result.finding_disposition.approved_evidence_ids == ("ev-1",)


def test_missing_evidence_id_fails_closed():
    item = finding(evidence_ids=("missing",))
    result = evaluate(item)
    assert result.finding_disposition.disposition == "WITHHELD_INSUFFICIENT_EVIDENCE"
    assert result.safety_issues[0].issue_type == "MISSING_EVIDENCE"
    assert result.finding_disposition.approved_evidence_ids == ()


def test_failed_lineage_fails_closed():
    result = evaluate(ev=evidence_output(packages=(evidence(lineage_status="MISMATCH"),)))
    assert result.finding_disposition.disposition == "WITHHELD_INSUFFICIENT_EVIDENCE"
    assert any(issue.issue_type == "FAILED_LINEAGE" and issue.blocking for issue in result.safety_issues)


def test_partial_lineage_is_not_approved_in_strict_mode():
    result = evaluate(ev=evidence_output(packages=(evidence(lineage_status="PARTIAL"),)))
    assert result.finding_disposition.disposition == "WITHHELD_INSUFFICIENT_EVIDENCE"


def test_version_unresolved_is_withheld():
    result = evaluate(ev=evidence_output(sufficiency="VERSION_UNRESOLVED", resolution_status="NOT_RESOLVED"))
    assert result.finding_disposition.disposition == "WITHHELD_INSUFFICIENT_EVIDENCE"
    assert any(issue.issue_type == "VERSION_UNRESOLVED" for issue in result.safety_issues)


def test_unresolved_applicability_is_withheld():
    result = evaluate(ev=evidence_output(packages=(evidence(applicability_status="DATE_UNRESOLVED"),)))
    assert any(issue.issue_type == "VERSION_UNRESOLVED" for issue in result.safety_issues)


def test_entity_unresolved_is_withheld():
    result = evaluate(ev=evidence_output(sufficiency="ENTITY_UNRESOLVED", resolution_status="NOT_RESOLVED"))
    assert any(issue.issue_type == "ENTITY_UNRESOLVED" for issue in result.safety_issues)


def test_material_conflict_is_withheld():
    conflict = EvidenceConflict("conflict-1", "copay", ("ev-1",), "SOURCE_DISAGREEMENT", None, None, "UNRESOLVED", "HIGH")
    result = evaluate(ev=evidence_output(conflicts=(conflict,), resolution_status="CONFLICTING", sufficiency="CONFLICTING"))
    assert result.finding_disposition.disposition == "WITHHELD_CONFLICT"
    assert any(issue.issue_type == "MATERIAL_CONFLICT" for issue in result.safety_issues)


def test_resolved_nonmaterial_conflict_does_not_block():
    conflict = EvidenceConflict("conflict-1", "copay", ("ev-1",), "SOURCE_DISAGREEMENT", "ev-1", "authority", "RESOLVED_BY_AUTHORITY", "LOW")
    result = evaluate(ev=evidence_output(conflicts=(conflict,)))
    assert result.finding_disposition.disposition == "APPROVED"


def test_unsupported_finding_is_withheld():
    item = finding(finding_status="UNSUPPORTED")
    result = evaluate(item)
    assert result.finding_disposition.disposition == "WITHHELD_UNSUPPORTED"
    assert any(issue.issue_type == "UNSUPPORTED_INFERENCE" for issue in result.safety_issues)


def test_not_reasoned_output_withholds_supported_looking_finding():
    item = finding()
    result = evaluate(item, ro=reasoning_output(item, reasoning_status="NOT_REASONED", reasoning_sufficiency="UNSUPPORTED"))
    assert result.finding_disposition.disposition == "WITHHELD_UNSUPPORTED"


def test_case_specific_conditional_finding_requires_trigger_context():
    item = finding(finding_status="CONDITIONAL", scope="case-specific applicability")
    result = evaluate(item)
    assert result.finding_disposition.disposition == "WITHHELD_FOR_CLARIFICATION"
    assert result.clarifications[0].required_context_keys == ("trigger_status",)


def test_case_specific_conditional_finding_can_pass_with_trigger_context():
    item = finding(finding_status="CONDITIONAL", scope="case-specific applicability")
    result = evaluate(item, context={"trigger_status": "CONFIRMED"})
    assert result.finding_disposition.disposition == "APPROVED_WITH_LIMITATIONS"
    assert result.clarifications == ()


def test_general_supported_clause_meaning_does_not_require_context():
    result = evaluate(finding(finding_status="SUPPORTED", scope="general clause meaning"))
    assert result.finding_disposition.disposition == "APPROVED"


@pytest.mark.parametrize("operation", ["RECOMMEND_PRODUCT", "ASSESS_SUITABILITY", "CHOOSE_PRODUCT"])
def test_prohibited_recommendation_operations_are_blocked(operation):
    result = evaluate(operations=(operation,))
    assert result.finding_disposition.disposition == "BLOCKED"
    assert any(issue.issue_type == "RECOMMENDATION_WITHOUT_SUITABILITY" for issue in result.safety_issues)


def test_registry_policy_can_withhold_a_finding():
    policy = build_policy_definition(
        policy_id="policy_specific_uncertainty_v1", policy_version="1.0",
        domain="health", topic="conditional_copayment",
        finding_types=("CLAIM_COST_SHARING",), finding_statuses=("SUPPORTED",),
        derivation_types=("CONDITIONAL_DERIVATION",), reasoning_statuses=("REASONED",),
        reasoning_sufficiency_statuses=("COMPLETE",), evidence_resolution_statuses=("RESOLVED",),
        evidence_sufficiency_statuses=("COMPLETE",), strict_modes=("STRICT",),
        issue_type="POLICY_SPECIFIC_UNCERTAINTY", severity="HIGH",
        finding_disposition="WITHHELD_INSUFFICIENT_CONTEXT", decision_outcome="INSUFFICIENT_CONTEXT",
        blocking=True, evaluation_priority=1,
    )
    result = evaluate(registry=SafetyPolicyRegistry((policy,)))
    assert "policy_specific_uncertainty_v1" in result.matched_policy_ids
    assert result.finding_disposition.disposition == "BLOCKED"


def test_registry_nonblocking_policy_produces_approved_with_limitations():
    policy = build_policy_definition(
        policy_id="retain_scope_limitation_v1", policy_version="1.0",
        domain="health", topic="conditional_copayment",
        finding_types=("CLAIM_COST_SHARING",), finding_statuses=("SUPPORTED",),
        derivation_types=("CONDITIONAL_DERIVATION",), reasoning_statuses=("REASONED",),
        reasoning_sufficiency_statuses=("COMPLETE",), evidence_resolution_statuses=("RESOLVED",),
        evidence_sufficiency_statuses=("COMPLETE",), strict_modes=("STRICT",),
        issue_type="POLICY_SPECIFIC_UNCERTAINTY", severity="LOW",
        finding_disposition="APPROVED_WITH_LIMITATIONS", decision_outcome="APPROVED_WITH_LIMITATIONS",
        blocking=False, evaluation_priority=1,
    )
    result = evaluate(registry=SafetyPolicyRegistry((policy,)))
    assert result.finding_disposition.disposition == "APPROVED_WITH_LIMITATIONS"


def test_evaluation_is_deterministic():
    first = evaluate()
    second = evaluate()
    assert first == second


def test_inputs_are_not_mutated():
    item = finding()
    ev = evidence_output()
    ro = reasoning_output(item)
    before = (item, ev, ro)
    evaluate(item, ev=ev, ro=ro)
    assert before == (item, ev, ro)


def test_cross_stage_request_mismatch_is_rejected():
    item = finding()
    ev = replace(evidence_output(), request_id="other")
    with pytest.raises(FindingSafetyEvaluationError, match="request IDs"):
        evaluate(item, ev=ev)


def test_finding_must_belong_to_reasoning_output():
    item = finding(finding_id="other")
    with pytest.raises(FindingSafetyEvaluationError, match="belong"):
        evaluate(item, ro=reasoning_output(finding()))
