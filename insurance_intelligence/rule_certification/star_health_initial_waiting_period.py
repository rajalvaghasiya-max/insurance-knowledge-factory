"""Governed Star Comprehensive initial waiting-period certification case."""

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
STAR_COMPREHENSIVE_SOURCE_REGISTRATION_PATH = (
    "knowledge/factory/registry_backed/star_health_star_comprehensive/"
    "generic_source_registration/policy_wording_registration.json"
)
STAR_COMPREHENSIVE_SOURCE_REGISTRATION_SHA256 = (
    "0db438406f4e93c5b978cf76019c73e7c481c4bba2bbf9f94a3fb9ddffca5aa7"
)
STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_CANDIDATE_ID = "candidate_page_32"
STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_EVIDENCE_HASH = (
    "214466445fab2fd7fec30d951696479d4999bfc74aea13af40a1b80eddef77eb"
)
STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_REVIEWED_STATEMENT = (
    "Expenses related to treatment of any illness within 30 days from the first policy "
    "commencement date are excluded, except claims arising due to an accident, provided the "
    "same are covered. The exclusion does not apply if the Insured Person has Continuous "
    "Coverage for more than twelve months. The waiting period also applies to an enhanced "
    "Sum Insured when a higher Sum Insured is granted subsequently."
)


def _lineage(component_id: str) -> Lineage:
    return Lineage(
        source_artifact_path=STAR_COMPREHENSIVE_POLICY_WORDING_PATH,
        source_artifact_sha256=STAR_COMPREHENSIVE_POLICY_WORDING_SHA256,
        governed_record_path=STAR_COMPREHENSIVE_SOURCE_REGISTRATION_PATH,
        governed_record_sha256=STAR_COMPREHENSIVE_SOURCE_REGISTRATION_SHA256,
        binding_reference=(
            "registered_document:star_health_star_comprehensive_policy_wording_v1:"
            + STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_CANDIDATE_ID
        ),
        projection_reference=f"waiting_period:{component_id}",
        lineage_status="VERIFIED",
    )


def _evidence(component_id: str, requirement_type: str, claim: str) -> EvidencePackage:
    requirement_id = f"requirement:star-comprehensive-initial-waiting-period:{component_id}"
    return EvidencePackage(
        evidence_id=f"evidence:star-comprehensive-initial-waiting-period:{component_id}",
        requirement_id=requirement_id,
        subject_reference="product:star_health:star_comprehensive",
        governed_entity_reference=(
            "registered_document:star_health_star_comprehensive_policy_wording_v1:"
            + STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_CANDIDATE_ID
        ),
        field_or_topic=requirement_type,
        claim=claim,
        evidence_role="DEFINING",
        source_type="POLICY_WORDING",
        document_reference="star_health_star_comprehensive_policy_wording_v1",
        document_version=(
            "docver_star_health_star_comprehensive_policy_wording_v1_b1dbe8fb78646f75"
        ),
        effective_from=None,
        effective_to=None,
        page=32,
        section="III.3 30-day waiting period - Code Excl 03",
        source_excerpt=STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_REVIEWED_STATEMENT,
        normalized_fact_reference=f"star_comprehensive_initial_waiting_period:{component_id}",
        authority_rank=1,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=_lineage(component_id),
        retrieval_basis=(
            "registered_primary_legal_source",
            "primary_legal_policy_wording",
            STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_CANDIDATE_ID,
        ),
        confidence=1.0,
    )


def _requirement(component_id: str) -> RequirementResult:
    return RequirementResult(
        requirement_id=f"requirement:star-comprehensive-initial-waiting-period:{component_id}",
        status="SATISFIED",
        matched_evidence_ids=(
            f"evidence:star-comprehensive-initial-waiting-period:{component_id}",
        ),
        rejected_candidate_ids=(),
        missing_reason=None,
        authority_satisfied=True,
        version_satisfied=True,
        lineage_satisfied=True,
        conflict_status="NONE",
        confidence=1.0,
    )


def build_star_comprehensive_initial_waiting_period_case() -> RuleCertificationCaseFixture:
    """Build the exact Star Comprehensive initial waiting-period rule case."""
    case_id = "star_comprehensive_initial_waiting_period"
    component_claims = (
        (
            "waiting_period_duration",
            "WAITING_PERIOD_DURATION",
            "The initial waiting period is 30 days.",
        ),
        (
            "waiting_period_subject",
            "WAITING_PERIOD_SUBJECT",
            "Expenses related to treatment of any illness are excluded during the initial waiting period.",
        ),
        (
            "start_basis",
            "WAITING_PERIOD_START_BASIS",
            "The 30-day period is measured from the first policy commencement date.",
        ),
        (
            "applicability_scope",
            "APPLICABILITY_SCOPE",
            "The waiting period applies to an enhanced Sum Insured when a higher Sum Insured is granted subsequently.",
        ),
        (
            "continuity_or_credit_rule",
            "CONTINUITY_OR_CREDIT_RULE",
            "The exclusion does not apply if the Insured Person has Continuous Coverage for more than twelve months.",
        ),
        (
            "exception_condition",
            "EXCEPTION_CONDITION",
            "The exclusion does not apply to claims arising due to an accident, provided the same are covered.",
        ),
    )
    evidence = tuple(
        _evidence(component_id, requirement_type, claim)
        for component_id, requirement_type, claim in component_claims
    )
    requirements = tuple(
        _requirement(component_id) for component_id, _, _ in component_claims
    )
    expectation = build_rule_certification_expectation(
        certification_id=case_id,
        governed_subject_reference=(
            "registered_document:star_health_star_comprehensive_policy_wording_v1:"
            + STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_CANDIDATE_ID
        ),
        topic_id="waiting_period",
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
            "This certification uses registered primary policy-wording evidence and does not "
            "itself publish a customer-facing rule.",
            "The phrase 'within 30 days from the first policy commencement date' does not "
            "authorize an exact first-active calendar date or activation convention.",
            "The accident exception applies only when the claim is otherwise covered and "
            "does not establish claim admissibility.",
            "Policy-specific applicability remains subject to the Policy Schedule, "
            "Endorsements, continuity facts, and other policy terms.",
            "This certification does not guarantee claim approval or payment.",
        ),
        resolution_trace=(),
        resolution_status="RESOLVED",
        confidence=1.0,
    )
    return RuleCertificationCaseFixture(
        case_id=case_id,
        description=(
            "Exact Star Comprehensive 30-day initial waiting-period certification using the "
            "existing generic waiting-period topic."
        ),
        domain="health",
        expectation=expectation,
        evidence_output=output,
        expected_outcome="PASS",
    )
