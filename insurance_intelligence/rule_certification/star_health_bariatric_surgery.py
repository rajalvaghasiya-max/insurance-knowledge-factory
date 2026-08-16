"""Governed Star Comprehensive bariatric-surgery certification case (P2.2)."""

from __future__ import annotations

from insurance_intelligence.contracts.evidence import (
    EvidencePackage,
    EvidenceResolverOutput,
    Lineage,
    RequirementResult,
)
from insurance_intelligence.contracts.rule_certification import (
    build_component_certification_expectation,
    build_rule_certification_expectation,
)
from insurance_intelligence.rule_certification.fixtures import RuleCertificationCaseFixture

STAR_COMPREHENSIVE_POLICY_WORDING_PATH = (
    "archive/raw_documents/star_health/star_comprehensive_policy_wording_2025.pdf"
)
STAR_COMPREHENSIVE_POLICY_WORDING_SHA256 = (
    "b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f"
)
STAR_COMPREHENSIVE_BARIATRIC_CANDIDATE_ID = "candidate_page_15"
STAR_COMPREHENSIVE_BARIATRIC_EVIDENCE_HASH = (
    "efe143eab857a4813b51c68d510d9ce7b9aafc2525c7eb6e685dcc9bd318f32c"
)
STAR_COMPREHENSIVE_SOURCE_REGISTRATION_SHA256 = (
    "0db438406f4e93c5b978cf76019c73e7c481c4bba2bbf9f94a3fb9ddffca5aa7"
)
STAR_COMPREHENSIVE_BARIATRIC_SOURCE_EXCERPT = (
    "Bariatric surgery expenses are payable subject to the policy limits and special conditions. "
    "The insured must be above 18 years, the indication must be found appropriate by two qualified "
    "surgeons, prior approval for cashless treatment must be obtained, BMI must be greater than 40 "
    "or greater than 35 with co-morbidities, and traditional weight-loss methods must have failed. "
    "The benefit does not apply for the listed endocrine, substance-abuse, psychiatric, comprehension, "
    "or cosmetic-surgery circumstances."
)


def _lineage(component_id: str) -> Lineage:
    return Lineage(
        source_artifact_path=STAR_COMPREHENSIVE_POLICY_WORDING_PATH,
        source_artifact_sha256=STAR_COMPREHENSIVE_POLICY_WORDING_SHA256,
        governed_record_path=(
            "knowledge/factory/registry_backed/star_health_star_comprehensive/"
            "generic_source_registration/policy_wording_registration.json"
        ),
        governed_record_sha256=STAR_COMPREHENSIVE_SOURCE_REGISTRATION_SHA256,
        binding_reference=(
            "registered_document:star_health_star_comprehensive_policy_wording_v1:"
            + STAR_COMPREHENSIVE_BARIATRIC_CANDIDATE_ID
        ),
        projection_reference=f"eligibility_and_consequence:{component_id}",
        lineage_status="VERIFIED",
    )


def _evidence(component_id: str, requirement_type: str, claim: str) -> EvidencePackage:
    requirement_id = f"requirement:star-comprehensive-bariatric:{component_id}"
    return EvidencePackage(
        evidence_id=f"evidence:star-comprehensive-bariatric:{component_id}",
        requirement_id=requirement_id,
        subject_reference="product:star_health:star_comprehensive",
        governed_entity_reference=(
            "registered_document:star_health_star_comprehensive_policy_wording_v1"
        ),
        field_or_topic=requirement_type,
        claim=claim,
        evidence_role="DEFINING",
        source_type="POLICY_WORDING",
        document_reference="star_health_star_comprehensive_policy_wording_v1",
        document_version="docver_star_health_star_comprehensive_policy_wording_v1_b1dbe8fb78646f75",
        effective_from=None,
        effective_to=None,
        page=15,
        section="II.15 Bariatric Surgery",
        source_excerpt=STAR_COMPREHENSIVE_BARIATRIC_SOURCE_EXCERPT,
        normalized_fact_reference=f"star_comprehensive_bariatric:{component_id}",
        authority_rank=1,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=_lineage(component_id),
        retrieval_basis=(
            "registered_primary_legal_source",
            "primary_legal_policy_wording",
            STAR_COMPREHENSIVE_BARIATRIC_CANDIDATE_ID,
        ),
        confidence=1.0,
    )


def _requirement(component_id: str) -> RequirementResult:
    return RequirementResult(
        requirement_id=f"requirement:star-comprehensive-bariatric:{component_id}",
        status="SATISFIED",
        matched_evidence_ids=(f"evidence:star-comprehensive-bariatric:{component_id}",),
        rejected_candidate_ids=(),
        missing_reason=None,
        authority_satisfied=True,
        version_satisfied=True,
        lineage_satisfied=True,
        conflict_status="NONE",
        confidence=1.0,
    )


def build_star_comprehensive_bariatric_surgery_case() -> RuleCertificationCaseFixture:
    """Build the governed Star bariatric eligibility-and-consequence case."""
    case_id = "star_comprehensive_bariatric_surgery"
    component_claims = (
        (
            "eligibility_criteria",
            "ELIGIBILITY_CRITERIA",
            "Eligibility requires age above 18, two-surgeon appropriateness, prior cashless approval, qualifying BMI, and failed traditional weight-loss methods.",
        ),
        (
            "applicability_scope",
            "APPLICABILITY_SCOPE",
            "The rule applies to hospitalization for bariatric surgery and its complications during the policy period, subject to the stated limits and cashless process.",
        ),
        (
            "eligible_consequence",
            "ELIGIBLE_CONSEQUENCE",
            "When all eligibility conditions are satisfied, covered bariatric hospitalization expenses are payable up to the applicable policy limit.",
        ),
        (
            "ineligible_consequence",
            "INELIGIBLE_CONSEQUENCE",
            "The benefit does not apply when any listed non-applicability circumstance is present or the required eligibility conditions are not satisfied.",
        ),
        (
            "exception_condition",
            "EXCEPTION_CONDITION",
            "Non-applicability includes specified endocrine causes, current drug or alcohol abuse, uncontrolled severe psychiatric illness, lack of comprehension, and cosmetic reasons.",
        ),
    )
    evidence = tuple(
        _evidence(component_id, requirement_type, claim)
        for component_id, requirement_type, claim in component_claims
    )
    requirements = tuple(_requirement(component_id) for component_id, _, _ in component_claims)
    expectation = build_rule_certification_expectation(
        certification_id=case_id,
        governed_subject_reference=(
            "registered_document:star_health_star_comprehensive_policy_wording_v1:"
            + STAR_COMPREHENSIVE_BARIATRIC_CANDIDATE_ID
        ),
        topic_id="eligibility_and_consequence",
        topic_version="1.0",
        expected_completeness_statuses=("COMPLETE",),
        expected_explanation_permitted=True,
        component_expectations=tuple(
            build_component_certification_expectation(
                component_id=component_id,
                acceptable_statuses=("SATISFIED",),
            )
            for component_id, _, _ in component_claims
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
            "Certification uses registered policy-wording evidence and does not itself publish a customer-facing rule.",
            "The certification describes contractual eligibility semantics and does not decide individual medical suitability.",
            "Satisfying the listed conditions does not guarantee claim admissibility or payment.",
        ),
        resolution_trace=(),
        resolution_status="RESOLVED",
        confidence=1.0,
    )
    return RuleCertificationCaseFixture(
        case_id=case_id,
        description=(
            "Star Comprehensive bariatric-surgery eligibility, payable consequence, and non-applicability certification case."
        ),
        domain="health",
        expectation=expectation,
        evidence_output=output,
        expected_outcome="PASS",
    )
