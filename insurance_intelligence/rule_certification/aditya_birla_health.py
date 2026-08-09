"""Cross-product governed certification cases for Aditya Birla Health."""

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

ACTIV_ONE_POLICY_INTELLIGENCE_PATH = (
    "knowledge/health/aditya_birla_health/activ_one/intelligence/policy_intelligence.json"
)
ACTIV_ONE_POLICY_WORDING_PATH = (
    "knowledge/health/aditya_birla_health/activ_one/documents/policy_wording.pdf"
)
ACTIV_ONE_SPECIFIED_WAITING_PERIOD_REFERENCE = "exclusion:D.1.2:specified-disease-waiting-period"
ACTIV_ONE_SPECIFIED_WAITING_PERIOD_TEXT_HASH = (
    "3f37bee53387b02d831eab255e58e620a9ce7083a645dce0b48d6b4aa961df67"
)
ACTIV_ONE_SPECIFIED_WAITING_PERIOD_STATEMENT = (
    "Expenses related to listed conditions, surgeries, or treatments are excluded until the "
    "expiry of 24 months of continuous coverage after inception of the first policy with the "
    "insurer. The exclusion does not apply to claims arising due to an accident. It applies "
    "afresh to an enhanced sum insured to the extent of the increase; where a listed condition "
    "also falls under the pre-existing-disease waiting period, the longer waiting period applies; "
    "and portability continuity credit reduces the waiting period to the extent of prior coverage."
)


def _lineage(component_id: str) -> Lineage:
    return Lineage(
        source_artifact_path=ACTIV_ONE_POLICY_WORDING_PATH,
        source_artifact_sha256=ACTIV_ONE_SPECIFIED_WAITING_PERIOD_TEXT_HASH,
        governed_record_path=ACTIV_ONE_POLICY_INTELLIGENCE_PATH,
        governed_record_sha256=ACTIV_ONE_SPECIFIED_WAITING_PERIOD_TEXT_HASH,
        binding_reference=ACTIV_ONE_SPECIFIED_WAITING_PERIOD_REFERENCE,
        projection_reference=f"waiting_period:{component_id}",
        lineage_status="VERIFIED",
    )


def _evidence(component_id: str, requirement_type: str, claim: str) -> EvidencePackage:
    requirement_id = f"requirement:activ-one-specified-waiting-period:{component_id}"
    return EvidencePackage(
        evidence_id=f"evidence:activ-one-specified-waiting-period:{component_id}",
        requirement_id=requirement_id,
        subject_reference="product:aditya_birla_health:activ_one",
        governed_entity_reference=ACTIV_ONE_SPECIFIED_WAITING_PERIOD_REFERENCE,
        field_or_topic=requirement_type,
        claim=claim,
        evidence_role="DEFINING",
        source_type="POLICY_WORDING",
        document_reference="aditya_birla_health_activ_one_policy_wording",
        document_version="ADIHLIP24097V012324",
        effective_from=None,
        effective_to=None,
        page=10,
        section="D.1.2 Specified disease / procedure Waiting Period (Code-Excl02)",
        source_excerpt=ACTIV_ONE_SPECIFIED_WAITING_PERIOD_STATEMENT,
        normalized_fact_reference=f"{ACTIV_ONE_SPECIFIED_WAITING_PERIOD_REFERENCE}:{component_id}",
        authority_rank=1,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=_lineage(component_id),
        retrieval_basis=(
            "validated_policy_intelligence",
            "primary_legal_policy_wording",
            "policy_wording_page_10",
        ),
        confidence=0.9,
    )


def _requirement(component_id: str) -> RequirementResult:
    return RequirementResult(
        requirement_id=f"requirement:activ-one-specified-waiting-period:{component_id}",
        status="SATISFIED",
        matched_evidence_ids=(f"evidence:activ-one-specified-waiting-period:{component_id}",),
        rejected_candidate_ids=(),
        missing_reason=None,
        authority_satisfied=True,
        version_satisfied=True,
        lineage_satisfied=True,
        conflict_status="NONE",
        confidence=0.9,
    )


def build_activ_one_specified_disease_waiting_period_case() -> RuleCertificationCaseFixture:
    """Build the governed Activ One specified-disease waiting-period replication case."""
    case_id = "activ_one_specified_disease_waiting_period"
    component_claims = (
        (
            "waiting_period_duration",
            "WAITING_PERIOD_DURATION",
            "The waiting period is 24 months of continuous coverage.",
        ),
        (
            "waiting_period_subject",
            "WAITING_PERIOD_SUBJECT",
            "The rule applies to listed conditions, surgeries, treatments, and their complications.",
        ),
        (
            "start_basis",
            "WAITING_PERIOD_START_BASIS",
            "The period is measured from inception of the first policy with the insurer.",
        ),
        (
            "applicability_scope",
            "APPLICABILITY_SCOPE",
            "The exclusion applies to covered expenses for the listed conditions and applies afresh to an enhanced sum insured to the extent of the increase.",
        ),
        (
            "continuity_or_credit_rule",
            "CONTINUITY_OR_CREDIT_RULE",
            "Portability continuity credit reduces the waiting period to the extent of prior coverage; where the PED period also applies, the longer period governs.",
        ),
        (
            "exception_condition",
            "EXCEPTION_CONDITION",
            "The exclusion does not apply to claims arising due to an accident.",
        ),
    )
    evidence = tuple(
        _evidence(component_id, requirement_type, claim)
        for component_id, requirement_type, claim in component_claims
    )
    requirements = tuple(_requirement(component_id) for component_id, _, _ in component_claims)
    expectation = build_rule_certification_expectation(
        certification_id=case_id,
        governed_subject_reference=ACTIV_ONE_SPECIFIED_WAITING_PERIOD_REFERENCE,
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
            "This replication case certifies the governed rule internally and does not itself publish customer-facing product knowledge.",
            "The rule describes contractual waiting-period conditions and does not guarantee claim payment or admissibility.",
        ),
        resolution_trace=(),
        resolution_status="RESOLVED",
        confidence=0.9,
    )
    return RuleCertificationCaseFixture(
        case_id=case_id,
        description=(
            "Cross-product replication of the generic waiting-period certification framework "
            "using Activ One's specified-disease waiting period."
        ),
        domain="health",
        expectation=expectation,
        evidence_output=output,
        expected_outcome="PASS",
    )
