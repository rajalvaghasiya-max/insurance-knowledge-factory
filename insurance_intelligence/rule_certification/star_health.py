"""Governed Star Health certification cases (MO-023J.4)."""

from __future__ import annotations

from insurance_intelligence.contracts.evidence import (
    EvidencePackage,
    EvidenceResolverOutput,
    Lineage,
    RequirementResult,
)
from insurance_intelligence.contracts.rule_certification import (
    RuleCertificationResult,
    build_component_certification_expectation,
    build_rule_certification_expectation,
)
from insurance_intelligence.reasoning.rules import (
    build_rule_input,
    conditional_copayment_obligation,
)
from insurance_intelligence.rule_certification.fixtures import RuleCertificationCaseFixture
from insurance_intelligence.rule_certification.runner import run_rule_certification
from insurance_intelligence.topic_completeness.star_pilot_profiles import (
    build_star_conditional_copayment_profile,
)

STAR_COMPREHENSIVE_COPAYMENT_BINDING_PATH = (
    "knowledge/factory/registry_backed/star_health_star_comprehensive/"
    "generic_legal_condition_binding/"
    "star_health_star_comprehensive_conditional_copayment.json"
)
STAR_COMPREHENSIVE_COPAYMENT_ASSERTION_ID = (
    "ga_star_comprehensive_entry_age_61_conditional_copayment_v1"
)
STAR_COMPREHENSIVE_COPAYMENT_EVIDENCE_HASH = (
    "ea3aa9a64bd799fbdcc52bdebb48a5b6917c90673451cf84230005506bb09594"
)
STAR_COMPREHENSIVE_POLICY_WORDING_SHA256 = (
    "b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f"
)
STAR_COMPREHENSIVE_COPAYMENT_BINDING_SHA256 = (
    "caaff2add0217b93a77b77afc862f26872ed9146c4f14054d4c85eaaff8bb984"
)
STAR_COMPREHENSIVE_COPAYMENT_REVIEWED_STATEMENT = (
    "Star Comprehensive applies a 10% co-payment to each and every claim for fresh as well as "
    "renewal policies where the insured person's age at entry is 61 years or above. The "
    "co-payment does not apply where the insured person entered the policy before attaining 61 "
    "years of age and renewed continuously without a break. The policy wording limits this "
    "co-payment to Sections II.1, II.2, II.3, II.4, II.5, II.6, II.7, II.8, II.9, II.10, "
    "II.11, II.15 and II.25."
)


def _lineage(component_id: str) -> Lineage:
    return Lineage(
        source_artifact_path=(
            "archive/raw_documents/star_health/star_comprehensive_policy_wording_2025.pdf"
        ),
        source_artifact_sha256=STAR_COMPREHENSIVE_POLICY_WORDING_SHA256,
        governed_record_path=STAR_COMPREHENSIVE_COPAYMENT_BINDING_PATH,
        governed_record_sha256=STAR_COMPREHENSIVE_COPAYMENT_BINDING_SHA256,
        binding_reference=f"assertion:{STAR_COMPREHENSIVE_COPAYMENT_ASSERTION_ID}",
        projection_reference=f"conditional_obligation:{component_id}",
        lineage_status="VERIFIED",
    )


def _raw_governed_evidence() -> EvidencePackage:
    """Return the single reviewed Star statement consumed by production reasoning."""
    return EvidencePackage(
        evidence_id="evidence:star-comprehensive-copayment:governed-statement",
        requirement_id="requirement:star-comprehensive-copayment:governed-statement",
        subject_reference="product:star_health:star_comprehensive",
        governed_entity_reference="assertion:" + STAR_COMPREHENSIVE_COPAYMENT_ASSERTION_ID,
        field_or_topic="conditional_copayment",
        claim=STAR_COMPREHENSIVE_COPAYMENT_REVIEWED_STATEMENT,
        evidence_role="DEFINING",
        source_type="POLICY_WORDING",
        document_reference="star_health_star_comprehensive_policy_wording_v1",
        document_version="docver_star_health_star_comprehensive_policy_wording_v1_b1dbe8fb78646f75",
        effective_from=None,
        effective_to=None,
        page=39,
        section="Conditional co-payment",
        source_excerpt=STAR_COMPREHENSIVE_COPAYMENT_REVIEWED_STATEMENT,
        normalized_fact_reference=STAR_COMPREHENSIVE_COPAYMENT_ASSERTION_ID,
        authority_rank=1,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=_lineage("governed_statement"),
        retrieval_basis=(
            "reviewed_generic_legal_condition_binding",
            "primary_legal_policy_wording",
            "candidate_page_39",
        ),
        confidence=1.0,
    )


def extract_star_comprehensive_conditional_copayment_finding():
    """Run the real reviewed Star statement through production semantic extraction."""
    raw = _raw_governed_evidence()
    rule_input = build_rule_input(
        requirement_id=raw.requirement_id,
        evidence=(raw,),
        approved_context={},
        scope="star_health:star_comprehensive",
    )
    findings = conditional_copayment_obligation(rule_input)
    if len(findings) != 1:
        raise ValueError("Star copayment production extraction must yield exactly one finding")
    return findings[0]


def _evidence(component_id: str, requirement_type: str, claim: str) -> EvidencePackage:
    requirement_id = f"requirement:star-comprehensive-copayment:{component_id}"
    return EvidencePackage(
        evidence_id=f"evidence:star-comprehensive-copayment:{component_id}",
        requirement_id=requirement_id,
        subject_reference="product:star_health:star_comprehensive",
        governed_entity_reference="assertion:" + STAR_COMPREHENSIVE_COPAYMENT_ASSERTION_ID,
        field_or_topic=requirement_type,
        claim=claim,
        evidence_role="DEFINING",
        source_type="POLICY_WORDING",
        document_reference="star_health_star_comprehensive_policy_wording_v1",
        document_version="docver_star_health_star_comprehensive_policy_wording_v1_b1dbe8fb78646f75",
        effective_from=None,
        effective_to=None,
        page=39,
        section="Conditional co-payment",
        source_excerpt=STAR_COMPREHENSIVE_COPAYMENT_REVIEWED_STATEMENT,
        normalized_fact_reference=f"{STAR_COMPREHENSIVE_COPAYMENT_ASSERTION_ID}:{component_id}",
        authority_rank=1,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=_lineage(component_id),
        retrieval_basis=(
            "production_conditional_copayment_obligation",
            "reviewed_generic_legal_condition_binding",
            "primary_legal_policy_wording",
            "candidate_page_39",
        ),
        confidence=1.0,
    )


def _requirement(component_id: str) -> RequirementResult:
    return RequirementResult(
        requirement_id=f"requirement:star-comprehensive-copayment:{component_id}",
        status="SATISFIED",
        matched_evidence_ids=(f"evidence:star-comprehensive-copayment:{component_id}",),
        rejected_candidate_ids=(),
        missing_reason=None,
        authority_satisfied=True,
        version_satisfied=True,
        lineage_satisfied=True,
        conflict_status="NONE",
        confidence=1.0,
    )


def _production_component_claims() -> tuple[tuple[str, str, str], ...]:
    finding = extract_star_comprehensive_conditional_copayment_finding()
    components: list[tuple[str, str, str]] = [
        ("obligation_value", "OBLIGATION_VALUE", finding.object_or_effect),
        ("trigger_condition", "TRIGGER_CONDITION", finding.trigger or ""),
        (
            "calculation_basis",
            "CALCULATION_BASIS",
            "The documented 10% co-payment is calculated against each and every claim within the stated scope.",
        ),
    ]
    if finding.applicability_scope:
        components.append(
            ("applicability_scope", "APPLICABILITY_SCOPE", finding.applicability_scope)
        )
    if finding.exception:
        components.append(
            ("exception_condition", "EXCEPTION_CONDITION", finding.exception)
        )
    return tuple(components)


def build_star_comprehensive_conditional_copayment_case() -> RuleCertificationCaseFixture:
    """Build the Star case from production extraction of the governed reviewed statement."""
    case_id = "star_comprehensive_conditional_copayment"
    component_claims = _production_component_claims()
    evidence = tuple(
        _evidence(component_id, requirement_type, claim)
        for component_id, requirement_type, claim in component_claims
    )
    requirements = tuple(_requirement(component_id) for component_id, _, _ in component_claims)
    expectation_component_ids = (
        "obligation_value",
        "trigger_condition",
        "applicability_scope",
        "exception_condition",
        "calculation_basis",
    )
    expectation = build_rule_certification_expectation(
        certification_id=case_id,
        governed_subject_reference="assertion:" + STAR_COMPREHENSIVE_COPAYMENT_ASSERTION_ID,
        topic_id="conditional_obligation",
        topic_version="1.0",
        expected_completeness_statuses=("COMPLETE",),
        expected_explanation_permitted=True,
        component_expectations=tuple(
            build_component_certification_expectation(
                component_id=component_id,
                acceptable_statuses=("SATISFIED",),
            )
            for component_id in expectation_component_ids
        ),
    )
    output = EvidenceResolverOutput(
        contract_version="1.0",
        request_id="request:" + case_id,
        resolution_id="resolution:" + case_id,
        evidence_packages=evidence,
        requirement_results=requirements,
        entity_resolutions=(),
        document_resolutions=(),
        conflicts=(),
        missing_evidence=(),
        sufficiency="COMPLETE",
        limitations=(
            "The governed binding is bound_not_published and is used here only for internal certification.",
            "This rule describes a contractual co-payment mechanism and does not guarantee claim payment.",
        ),
        resolution_trace=(),
        resolution_status="RESOLVED",
        confidence=1.0,
    )
    return RuleCertificationCaseFixture(
        case_id=case_id,
        description=(
            "Star Comprehensive entry-age conditional co-payment certification built from production semantic extraction."
        ),
        domain="health",
        expectation=expectation,
        evidence_output=output,
        expected_outcome="PASS",
    )


def run_star_comprehensive_conditional_copayment_certification(
    *,
    evidence_output: EvidenceResolverOutput | None = None,
) -> RuleCertificationResult:
    """Run the Star copayment case with its product-specific completeness profile."""
    case = build_star_comprehensive_conditional_copayment_case()
    return run_rule_certification(
        expectation=case.expectation,
        evidence_output=evidence_output or case.evidence_output,
        domain=case.domain,
        profile=build_star_conditional_copayment_profile(),
    )
