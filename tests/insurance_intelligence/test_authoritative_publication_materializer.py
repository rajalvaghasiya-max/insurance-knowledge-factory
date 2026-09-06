from __future__ import annotations

import pytest

from insurance_intelligence.authoritative_publication.materializer import (
    AuthoritativePublicationMaterializationError,
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
from insurance_intelligence.evidence.published_artifact_store import (
    load_published_evidence_source,
    persist_published_evidence_source,
)

SUBJECT = "governed_fact:generic:duration"
CERTIFICATION_ID = "certification:generic:duration"
COMPONENT_ID = "duration"
EVIDENCE_ID = "evidence:generic:duration"
BOUNDARY = "The governed binding remains bound_not_published and is used only for internal certification."
SAFETY_LIMITATION = "This fact does not determine customer-specific eligibility or claim payment."


def _evidence() -> EvidenceResolverOutput:
    requirement_id = "requirement:generic:duration"
    return EvidenceResolverOutput(
        contract_version="1.0",
        request_id="request:generic:duration",
        resolution_id="resolution:generic:duration",
        evidence_packages=(
            EvidencePackage(
                evidence_id=EVIDENCE_ID,
                requirement_id=requirement_id,
                subject_reference=SUBJECT,
                governed_entity_reference=SUBJECT,
                field_or_topic="DURATION",
                claim="The governed duration is 36 months.",
                evidence_role="DEFINING",
                source_type="POLICY_WORDING",
                document_reference="document:generic:policy",
                document_version="1",
                effective_from=None,
                effective_to=None,
                page=1,
                section="Governed fact",
                source_excerpt="The governed duration is 36 months.",
                normalized_fact_reference="generic:duration",
                authority_rank=1,
                authority_requirement="AUTHORITATIVE",
                version_status="CURRENT_APPLICABLE",
                applicability_status="APPLICABLE",
                lineage=Lineage(
                    source_artifact_path="knowledge/generic/policy.pdf",
                    source_artifact_sha256="a" * 64,
                    governed_record_path="knowledge/generic/binding.json",
                    governed_record_sha256="b" * 64,
                    binding_reference="binding:generic:duration",
                    projection_reference="projection:generic:duration",
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
        request_id="request:generic:duration",
        resolution_id="resolution:generic:duration",
        resolution_status="RESOLVED",
        evidence_sufficiency="COMPLETE",
        topic_id="generic_duration",
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
        trace_references=("certification-trace:generic:duration",),
    )


def _authorization(*, subject=SUBJECT, certification_id=CERTIFICATION_ID):
    return build_publication_boundary_authorization(
        authorization_id="authorization:generic:duration",
        governed_subject_reference=subject,
        certification_id=certification_id,
        resolved_boundary_tokens=("bound_not_published",),
        authorization_authority="governed publication boundary authority",
        trace_references=("authorization-trace:generic:duration",),
    )


def _component(*, evidence_reference=EVIDENCE_ID):
    return build_governed_semantic_component(
        component_id=COMPONENT_ID,
        status="SATISFIED",
        evidence_references=(evidence_reference,),
    )


def _request(*, authorization=None, component=None, limitations=(SAFETY_LIMITATION,)):
    return build_authoritative_publication_materialization_request(
        decision_id="publication-decision:generic:duration",
        publication_id="authoritative-publication:generic:duration",
        projection_id="publication-projection:generic:duration",
        decision_reasons=("Publish an explicitly certified governed fact.",),
        decision_authority="governed publication decision authority",
        publication_authority="governed authoritative publication authority",
        limitations=limitations,
        semantic_components=(component or _component(),),
        boundary_authorization=authorization,
    )


def test_generic_materializer_requires_explicit_boundary_authorization():
    with pytest.raises(
        AuthoritativePublicationMaterializationError,
        match="publication decision did not permit",
    ):
        materialize_authoritative_published_evidence(
            certification=_certification(),
            certified_evidence=_evidence(),
            request=_request(),
        )


def test_generic_materializer_crosses_existing_gates_with_explicit_authorization():
    source = materialize_authoritative_published_evidence(
        certification=_certification(),
        certified_evidence=_evidence(),
        request=_request(authorization=_authorization()),
    )

    assert source.publication.publication_status == "AUTHORITATIVE"
    assert source.publication.authorization_id == "authorization:generic:duration"
    assert source.publication.resolved_certification_limitations == (BOUNDARY,)
    assert source.publication.limitations == (SAFETY_LIMITATION,)
    assert source.publication.semantic_components[0].evidence_references == (EVIDENCE_ID,)
    assert source.certified_evidence == _evidence()


def test_generic_materializer_rejects_missing_certified_evidence_reference():
    with pytest.raises(
        AuthoritativePublicationMaterializationError,
        match="missing certified evidence",
    ):
        materialize_authoritative_published_evidence(
            certification=_certification(),
            certified_evidence=_evidence(),
            request=_request(
                authorization=_authorization(),
                component=_component(evidence_reference="evidence:missing"),
            ),
        )


def test_generic_materializer_rejects_mismatched_authorization_identity():
    with pytest.raises(
        AuthoritativePublicationMaterializationError,
        match="authorization governed subject",
    ):
        materialize_authoritative_published_evidence(
            certification=_certification(),
            certified_evidence=_evidence(),
            request=_request(authorization=_authorization(subject="governed_fact:other")),
        )


def test_generic_materializer_does_not_publish_uncertified_component():
    with pytest.raises(
        AuthoritativePublicationMaterializationError,
        match="was not certified",
    ):
        materialize_authoritative_published_evidence(
            certification=_certification(),
            certified_evidence=_evidence(),
            request=build_authoritative_publication_materialization_request(
                decision_id="publication-decision:generic:other",
                publication_id="authoritative-publication:generic:other",
                projection_id="publication-projection:generic:other",
                decision_reasons=("Attempt unc ertified component publication.",),
                decision_authority="governed publication decision authority",
                publication_authority="governed authoritative publication authority",
                limitations=(SAFETY_LIMITATION,),
                semantic_components=(
                    build_governed_semantic_component(
                        component_id="other_component",
                        status="SATISFIED",
                        evidence_references=(EVIDENCE_ID,),
                    ),
                ),
                boundary_authorization=_authorization(),
            ),
        )


def test_generic_materializer_preserves_authoritative_gate_prohibited_language():
    with pytest.raises(Exception, match="Claim-payment guarantee language is not publishable"):
        materialize_authoritative_published_evidence(
            certification=_certification(),
            certified_evidence=_evidence(),
            request=_request(
                authorization=_authorization(),
                limitations=("This guarantee claim payment.",),
            ),
        )


def test_generic_materializer_round_trips_through_existing_artifact_store(tmp_path):
    source = materialize_authoritative_published_evidence(
        certification=_certification(),
        certified_evidence=_evidence(),
        request=_request(authorization=_authorization()),
    )
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
    assert reloaded == source
