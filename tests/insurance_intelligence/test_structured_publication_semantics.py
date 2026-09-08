from __future__ import annotations

from insurance_intelligence.authoritative_publication.materializer import (
    build_authoritative_publication_materialization_request,
    materialize_authoritative_published_evidence,
)
from insurance_intelligence.contracts.authoritative_publication import (
    build_governed_semantic_component,
)
from insurance_intelligence.contracts.evidence import (
    EvidencePackage,
    EvidenceResolverOutput,
    Lineage,
    RequirementResult,
)
from insurance_intelligence.contracts.publication_decision import (
    build_publication_boundary_authorization,
)
from insurance_intelligence.contracts.rule_certification import (
    ComponentCertificationCheck,
    RuleCertificationResult,
)
from insurance_intelligence.contracts.semantic import build_governed_semantic_attribute
from insurance_intelligence.evidence.published_artifact_store import (
    load_published_evidence_source,
    persist_published_evidence_source,
)
from insurance_intelligence.evidence.published_materialization import (
    materialize_published_requirement,
)

SUBJECT = "governed_fact:generic:conditional-copayment"
CERTIFICATION_ID = "certification:generic:conditional-copayment"
COMPONENT_ID = "conditional_copayment_rule"
EVIDENCE_ID = "evidence:generic:conditional-copayment"
BOUNDARY = "The governed binding remains bound_not_published and is used only for internal certification."
SAFETY_LIMITATION = "This fact does not determine customer-specific eligibility or claim payment."
TRIGGER = "reimbursement claim was not pre-approved"
RATE = "20%"


def _evidence() -> EvidenceResolverOutput:
    requirement_id = "requirement:generic:conditional-copayment"
    return EvidenceResolverOutput(
        contract_version="1.0",
        request_id="request:generic:conditional-copayment",
        resolution_id="resolution:generic:conditional-copayment",
        evidence_packages=(
            EvidencePackage(
                evidence_id=EVIDENCE_ID,
                requirement_id=requirement_id,
                subject_reference=SUBJECT,
                governed_entity_reference=SUBJECT,
                field_or_topic="conditional_copayment",
                claim="A reviewed conditional co-payment rule is certified.",
                evidence_role="DEFINING",
                source_type="POLICY_WORDING",
                document_reference="document:generic:policy",
                document_version="1",
                effective_from=None,
                effective_to=None,
                page=1,
                section="Conditional co-payment",
                source_excerpt="A reviewed conditional co-payment rule is certified.",
                normalized_fact_reference="generic:conditional-copayment",
                authority_rank=1,
                authority_requirement="AUTHORITATIVE",
                version_status="CURRENT_APPLICABLE",
                applicability_status="APPLICABLE",
                lineage=Lineage(
                    source_artifact_path="knowledge/generic/policy.pdf",
                    source_artifact_sha256="a" * 64,
                    governed_record_path="knowledge/generic/binding.json",
                    governed_record_sha256="b" * 64,
                    binding_reference="binding:generic:conditional-copayment",
                    projection_reference="projection:generic:conditional-copayment",
                    lineage_status="VERIFIED",
                ),
                retrieval_basis=("reviewed_binding",),
                confidence=1.0,
            ),
        ),
        requirement_results=(
            RequirementResult(
                requirement_id=requirement_id,
                status="SATISFIED",
                matched_evidence_ids=(EVIDENCE_ID,),
                rejected_candidate_ids=(),
                missing_reason=None,
                authority_satisfied=True,
                version_satisfied=True,
                lineage_satisfied=True,
                conflict_status="NONE",
                confidence=1.0,
            ),
        ),
        entity_resolutions=(),
        document_resolutions=(),
        conflicts=(),
        missing_evidence=(),
        sufficiency="COMPLETE",
        limitations=(BOUNDARY, SAFETY_LIMITATION),
        resolution_trace=(),
        resolution_status="RESOLVED",
        confidence=1.0,
    )


def _certification() -> RuleCertificationResult:
    return RuleCertificationResult(
        contract_version="1.0",
        certification_id=CERTIFICATION_ID,
        governed_subject_reference=SUBJECT,
        request_id="request:generic:conditional-copayment",
        resolution_id="resolution:generic:conditional-copayment",
        resolution_status="RESOLVED",
        evidence_sufficiency="COMPLETE",
        topic_id="conditional_copayment",
        topic_version="1.0",
        expected_completeness_statuses=("COMPLETE",),
        actual_completeness_status="COMPLETE",
        expected_explanation_permitted=True,
        actual_explanation_permitted=True,
        component_checks=(
            ComponentCertificationCheck(
                component_id=COMPONENT_ID,
                expected_statuses=("SATISFIED",),
                actual_status="SATISFIED",
                passed=True,
            ),
        ),
        outcome="PASS",
        failures=(),
        limitations=(BOUNDARY, SAFETY_LIMITATION),
        trace_references=("certification-trace:generic:conditional-copayment",),
    )


def _source():
    attributes = (
        build_governed_semantic_attribute(
            key="trigger",
            value=TRIGGER,
            evidence_references=(EVIDENCE_ID,),
        ),
        build_governed_semantic_attribute(
            key="rate",
            value=RATE,
            evidence_references=(EVIDENCE_ID,),
        ),
    )
    component = build_governed_semantic_component(
        component_id=COMPONENT_ID,
        status="SATISFIED",
        evidence_references=(EVIDENCE_ID,),
        semantic_attributes=attributes,
    )
    authorization = build_publication_boundary_authorization(
        authorization_id="authorization:generic:conditional-copayment",
        governed_subject_reference=SUBJECT,
        certification_id=CERTIFICATION_ID,
        resolved_boundary_tokens=("bound_not_published",),
        authorization_authority="governed publication boundary authority",
        trace_references=("authorization-trace:generic:conditional-copayment",),
    )
    request = build_authoritative_publication_materialization_request(
        decision_id="publication-decision:generic:conditional-copayment",
        publication_id="authoritative-publication:generic:conditional-copayment",
        projection_id="publication-projection:generic:conditional-copayment",
        decision_reasons=("Publish explicitly certified structured conditional semantics.",),
        decision_authority="governed publication decision authority",
        publication_authority="governed authoritative publication authority",
        limitations=(SAFETY_LIMITATION,),
        semantic_components=(component,),
        boundary_authorization=authorization,
    )
    return materialize_authoritative_published_evidence(
        certification=_certification(),
        certified_evidence=_evidence(),
        request=request,
    )


def test_trigger_and_rate_survive_publication_artifact_round_trip_without_claim_parsing(tmp_path):
    source = _source()
    publication_path = tmp_path / "publication.json"
    evidence_path = tmp_path / "evidence.json"
    persist_published_evidence_source(
        source=source,
        publication_path=publication_path,
        certified_evidence_path=evidence_path,
    )
    reloaded = load_published_evidence_source(
        publication_path=publication_path,
        certified_evidence_path=evidence_path,
    )

    component = reloaded.publication.semantic_components[0]
    assert {item.key: item.value for item in component.semantic_attributes} == {
        "rate": RATE,
        "trigger": TRIGGER,
    }
    assert RATE not in reloaded.certified_evidence.evidence_packages[0].claim
    assert TRIGGER not in reloaded.certified_evidence.evidence_packages[0].claim

    packages, requirement = materialize_published_requirement(
        source=reloaded,
        requirement_id="runtime-requirement",
        subject_reference="runtime-subject",
    )
    assert requirement.status == "SATISFIED"
    assert len(packages) == 1
    package = packages[0]
    assert {item.key: item.value for item in package.semantic_attributes} == {
        "rate": RATE,
        "trigger": TRIGGER,
    }
    assert all(item.evidence_references == (EVIDENCE_ID,) for item in package.semantic_attributes)
    assert RATE not in package.claim
    assert TRIGGER not in package.claim
