from __future__ import annotations

from insurance_intelligence.contracts.authoritative_publication import (
    AuthoritativePublicationRecord,
    build_governed_semantic_component,
)
from insurance_intelligence.contracts.decision import (
    build_approved_response_packet,
    build_finding_disposition,
    build_output as build_decision_output,
)
from insurance_intelligence.contracts.evidence import (
    EvidencePackage,
    EvidenceResolverOutput,
    Lineage,
    RequirementResult,
)
from insurance_intelligence.contracts.explanation import build_input as build_explanation_input
from insurance_intelligence.evidence.published_materialization import (
    PublishedEvidenceSource,
    materialize_published_requirement,
)
from insurance_intelligence.explanation.registry import build_style_definition
from insurance_intelligence.explanation.templates import render_explanation_templates
from insurance_intelligence.reasoning.rules import build_rule_input, direct_documented_fact


def _lineage() -> Lineage:
    return Lineage(
        source_artifact_path="source.pdf",
        source_artifact_sha256="a" * 64,
        governed_record_path="governed.json",
        governed_record_sha256="b" * 64,
        binding_reference="binding:test",
        projection_reference="projection:test",
        lineage_status="VERIFIED",
    )


def _package(evidence_id: str, requirement_id: str, topic: str, claim: str) -> EvidencePackage:
    return EvidencePackage(
        evidence_id=evidence_id,
        requirement_id=requirement_id,
        subject_reference="subject:test",
        governed_entity_reference="subject:test",
        field_or_topic=topic,
        claim=claim,
        evidence_role="DEFINING",
        source_type="POLICY_WORDING",
        document_reference="doc-test",
        document_version="1",
        effective_from=None,
        effective_to=None,
        page=1,
        section="test",
        source_excerpt=claim,
        normalized_fact_reference=f"fact:{topic}",
        authority_rank=1,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=_lineage(),
        retrieval_basis=("test",),
        confidence=1.0,
    )


def _source() -> PublishedEvidenceSource:
    primary = _package("cert-primary", "cert-req-1", "OBLIGATION_VALUE", "The obligation is 20%.")
    qualifying = _package(
        "cert-qualifying",
        "cert-req-2",
        "EXCEPTION_CONDITION",
        "scope_type=POLICY_WIDE; machine_enum=REAPPLIES_TO_ENHANCED_PORTION.",
    )
    evidence = EvidenceResolverOutput(
        contract_version="1.0",
        request_id="cert-request",
        resolution_id="cert-resolution",
        evidence_packages=(primary, qualifying),
        requirement_results=(
            RequirementResult("cert-req-1", "SATISFIED", ("cert-primary",), (), None, True, True, True, "NONE", 1.0),
            RequirementResult("cert-req-2", "SATISFIED", ("cert-qualifying",), (), None, True, True, True, "NONE", 1.0),
        ),
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
    publication = AuthoritativePublicationRecord(
        contract_version="1.0",
        publication_id="authoritative-publication:test:conditional_obligation",
        decision_id="decision:test",
        governed_subject_reference="subject:test",
        certification_id="cert:test",
        topic_id="conditional_obligation",
        topic_version="1.0",
        publication_status="AUTHORITATIVE",
        semantic_components=(
            build_governed_semantic_component(
                component_id="obligation_value",
                status="SATISFIED",
                evidence_references=("cert-primary",),
            ),
            build_governed_semantic_component(
                component_id="exception_condition",
                status="SATISFIED",
                evidence_references=("cert-qualifying",),
            ),
        ),
        limitations=(),
        certification_trace_references=("cert-trace",),
        evidence_trace_references=("cert-primary", "cert-qualifying"),
        publication_authority="test authority",
        publication_receipt_id="receipt-test",
    )
    return PublishedEvidenceSource(publication=publication, certified_evidence=evidence)


def test_customer_plain_language_keeps_unrequested_qualifying_machine_fact_out_of_meaning() -> None:
    packages, _ = materialize_published_requirement(
        source=_source(),
        requirement_id="runtime-req",
        subject_reference="requested_fact",
    )
    findings = direct_documented_fact(
        build_rule_input(
            requirement_id="runtime-req",
            evidence=packages,
            approved_context={},
            scope="product",
        )
    )
    packet = build_approved_response_packet(
        packet_id="packet-1",
        approved_finding_ids=tuple(item.finding_id for item in findings),
        approved_evidence_ids=tuple(
            evidence_id for item in findings for evidence_id in item.evidence_ids
        ),
    )
    decision = build_decision_output(
        request_id="request-1",
        decision_id="decision-1",
        decision="APPROVED",
        finding_dispositions=tuple(
            build_finding_disposition(
                finding_id=item.finding_id,
                disposition="APPROVED",
                basis="governed direct fact",
                approved_evidence_ids=item.evidence_ids,
                confidence=1.0,
            )
            for item in findings
        ),
        response_packet=packet,
        confidence=1.0,
    )
    rendered = render_explanation_templates(
        explanation_input=build_explanation_input(
            request_id="request-1",
            decision_output=decision,
        ),
        findings_by_id={item.finding_id: item for item in findings},
        style=build_style_definition(
            style_id="customer-simple-v1",
            style_version="1.0",
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_modes=("PLAIN_LANGUAGE",),
        ),
    )

    primary = [item for item in rendered.sections if item.section_type == "DIRECT_ANSWER"]
    meaning = [item for item in rendered.sections if item.section_type == "MEANING"]
    conditions = [item for item in rendered.sections if item.section_type == "CONDITION"]

    assert [item.text for item in primary] == ["The obligation is 20%."]
    assert not meaning
    assert len(conditions) == 1
    assert "REAPPLIES_TO_ENHANCED_PORTION" in conditions[0].text
