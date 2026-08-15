"""Legacy compatibility/parity fixture for the Star Comprehensive room-rent certification case.

This module preserves the original MO-023J.5 Python-coded Star case as a regression oracle while
Phase-2 Health scaling uses governed-data certification records materialized through the generic
rule-certification loader and unchanged generic runner.

Do not copy this module as the onboarding pattern for new products. New Health product semantics
should be represented as governed data/evidence against insurer-independent contracts unless real
product pressure proves a missing generic abstraction.
"""

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
STAR_COMPREHENSIVE_ROOM_RENT_CANDIDATE_ID = "candidate_page_9"
STAR_COMPREHENSIVE_ROOM_RENT_EVIDENCE_HASH = (
    "b17c1a2223d026d7c8be5c147230d0698aa4d6634ff02f13121206761ef30e1c"
)
STAR_COMPREHENSIVE_ROOM_RENT_SOURCE_EXCERPT = (
    "Room (Private Single A/C room), Boarding and Nursing Expenses as provided by the Hospital / "
    "Nursing Home. Any hospitalization expenses arising under this Policy, which vary based on "
    "the room rent occupied by the Insured Person will be considered in proportion to the room "
    "rent limit / room category stated in the Policy or actuals whichever is less."
)


def _lineage(component_id: str) -> Lineage:
    return Lineage(
        source_artifact_path=STAR_COMPREHENSIVE_POLICY_WORDING_PATH,
        source_artifact_sha256=STAR_COMPREHENSIVE_POLICY_WORDING_SHA256,
        governed_record_path=(
            "knowledge/factory/registry_backed/star_health_star_comprehensive/"
            "generic_source_registration/policy_wording_registration.json"
        ),
        governed_record_sha256=STAR_COMPREHENSIVE_ROOM_RENT_EVIDENCE_HASH,
        binding_reference=(
            "registered_document:star_health_star_comprehensive_policy_wording_v1:"
            + STAR_COMPREHENSIVE_ROOM_RENT_CANDIDATE_ID
        ),
        projection_reference=f"coverage_limit:{component_id}",
        lineage_status="VERIFIED",
    )


def _evidence(component_id: str, requirement_type: str, claim: str) -> EvidencePackage:
    requirement_id = f"requirement:star-comprehensive-room-rent:{component_id}"
    return EvidencePackage(
        evidence_id=f"evidence:star-comprehensive-room-rent:{component_id}",
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
        page=9,
        section="II.1 In-patient Treatment",
        source_excerpt=STAR_COMPREHENSIVE_ROOM_RENT_SOURCE_EXCERPT,
        normalized_fact_reference=f"star_comprehensive_room_rent:{component_id}",
        authority_rank=1,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=_lineage(component_id),
        retrieval_basis=(
            "registered_primary_legal_source",
            "primary_legal_policy_wording",
            STAR_COMPREHENSIVE_ROOM_RENT_CANDIDATE_ID,
        ),
        confidence=1.0,
    )


def _requirement(component_id: str) -> RequirementResult:
    return RequirementResult(
        requirement_id=f"requirement:star-comprehensive-room-rent:{component_id}",
        status="SATISFIED",
        matched_evidence_ids=(f"evidence:star-comprehensive-room-rent:{component_id}",),
        rejected_candidate_ids=(),
        missing_reason=None,
        authority_satisfied=True,
        version_satisfied=True,
        lineage_satisfied=True,
        conflict_status="NONE",
        confidence=1.0,
    )


def build_star_comprehensive_room_rent_case() -> RuleCertificationCaseFixture:
    """Build the historical Python-coded parity case for Star Comprehensive room rent."""
    case_id = "star_comprehensive_room_rent"
    component_claims = (
        (
            "covered_subject",
            "COVERED_SUBJECT",
            "In-patient room, boarding, nursing, and room-linked hospitalization expenses are covered subjects.",
        ),
        (
            "limit_value",
            "LIMIT_VALUE",
            "The permitted room category is a Private Single A/C room; no separate monetary room-rent cap is asserted.",
        ),
        (
            "limit_basis",
            "LIMIT_BASIS",
            "Room-linked expenses are considered using the policy-stated room category or actuals, whichever is less.",
        ),
        (
            "applicability_scope",
            "APPLICABILITY_SCOPE",
            "The rule applies to hospitalization expenses that vary based on the room rent occupied by the insured person.",
        ),
        (
            "excess_consequence",
            "EXCESS_CONSEQUENCE",
            "Expenses that vary with room rent are considered proportionately when the occupied room exceeds the permitted category.",
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
            + STAR_COMPREHENSIVE_ROOM_RENT_CANDIDATE_ID
        ),
        topic_id="coverage_limit",
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
            "Certification uses registered primary policy-wording evidence and does not itself publish a customer-facing rule.",
            "The policy wording specifies a room category, not a separate monetary room-rent cap.",
            "The proportional consideration mechanism does not guarantee admissibility or payment of any claim.",
        ),
        resolution_trace=(),
        resolution_status="RESOLVED",
        confidence=1.0,
    )
    return RuleCertificationCaseFixture(
        case_id=case_id,
        description=(
            "Exact Star Comprehensive Private Single A/C room-category and proportional-expense certification case."
        ),
        domain="health",
        expectation=expectation,
        evidence_output=output,
        expected_outcome="PASS",
    )
