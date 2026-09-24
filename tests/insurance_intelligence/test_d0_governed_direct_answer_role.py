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
from insurance_intelligence.evidence.published_materialization import (
    PublishedEvidenceSource,
    materialize_published_requirement,
)
from insurance_intelligence.explanation.registry import (
    ExplanationStyleRegistry,
    build_style_definition,
)
from insurance_intelligence.explanation.templates import render_explanation_templates
from insurance_intelligence.contracts.explanation import build_input as build_explanation_input
from insurance_intelligence.reasoning.rules import (
    build_rule_input,
    direct_documented_fact,
)


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


def _certified_package(
    *,
    evidence_id: str,
    requirement_id: str,
    field_or_topic: str,
    claim: str,
) -> EvidencePackage:
    return EvidencePackage(
        evidence_id=evidence_id,
        requirement_id=requirement_id,
        subject_reference="subject:test",
        governed_entity_reference="subject:test",
        field_or_topic=field_or_topic,
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
        normalized_fact_reference=f"fact:{field_or_topic}",
        authority_rank=1,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=_lineage(),
        retrieval_basis=("test",),
        confidence=1.0,
    )


def _source(*, component_ids: tuple[str, ...]) -> PublishedEvidenceSource:
    packages = []
    results = []
    components = []
    topic_to_claim = {
        "obligation_value": ("OBLIGATION_VALUE", "The obligation is 20%."),
        "trigger_condition": ("TRIGGER_CONDITION", "The trigger is age 61 or above."),
        "exception_condition": ("EXCEPTION_CONDITION", "The exception is a documented waiver."),
    }
    for index, component_id in enumerate(component_ids, start=1):
        field_or_topic, claim = topic_to_claim[component_id]
        evidence_id = f"certified-{component_id}"
        requirement_id = f"cert-req-{index}"
        packages.append(
            _certified_package(
                evidence_id=evidence_id,
                requirement_id=requirement_id,
                field_or_topic=field_or_topic,
                claim=claim,
            )
        )
        results.append(
            RequirementResult(
                requirement_id=requirement_id,
                status="SATISFIED",
                matched_evidence_ids=(evidence_id,),
                rejected_candidate_ids=(),
                missing_reason=None,
                authority_satisfied=True,
                version_satisfied=True,
                lineage_satisfied=True,
                conflict_status="NONE",
                confidence=1.0,
            )
        )
        components.append(
            build_governed_semantic_component(
                component_id=component_id,
                status="SATISFIED",
                evidence_references=(evidence_id,),
            )
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
        semantic_components=tuple(components),
        limitations=(),
        certification_trace_references=("cert-trace",),
        evidence_trace_references=tuple(item.evidence_id for item in packages),
        publication_authority="test authority",
        publication_receipt_id="receipt-test",
    )
    evidence = EvidenceResolverOutput(
        contract_version="1.0",
        request_id="cert-request",
        resolution_id="cert-resolution",
        evidence_packages=tuple(packages),
        requirement_results=tuple(results),
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
    return PublishedEvidenceSource(publication=publication, certified_evidence=evidence)


def _role(package: EvidencePackage) -> str | None:
    values = [
        item.value
        for item in package.semantic_attributes
        if item.key == "answer_role"
    ]
    assert len(values) <= 1
    return values[0] if values else None


def test_untuned_topic_derives_primary_and_qualifying_roles_from_governed_components() -> None:
    source = _source(component_ids=("obligation_value", "exception_condition"))

    packages, _ = materialize_published_requirement(
        source=source,
        requirement_id="runtime-req",
        subject_reference="requested_fact",
    )

    roles = {item.field_or_topic: _role(item) for item in packages}
    assert roles == {
        "OBLIGATION_VALUE": "PRIMARY",
        "EXCEPTION_CONDITION": "QUALIFYING",
    }

    findings = direct_documented_fact(
        build_rule_input(
            requirement_id="runtime-req",
            evidence=packages,
            approved_context={},
            scope="product",
        )
    )
    finding_roles = {
        item.object_or_effect: next(
            (
                attr.value
                for attr in item.semantic_attributes
                if attr.key == "answer_role"
            ),
            None,
        )
        for item in findings
    }
    assert finding_roles["The obligation is 20%."] == "PRIMARY"
    assert finding_roles["The exception is a documented waiver."] == "QUALIFYING"


def test_multiple_published_required_components_do_not_invent_primary_role() -> None:
    source = _source(component_ids=("obligation_value", "trigger_condition"))

    packages, _ = materialize_published_requirement(
        source=source,
        requirement_id="runtime-req",
        subject_reference="requested_fact",
    )

    assert all(_role(item) is None for item in packages)


def _decision_for_findings(findings):
    dispositions = tuple(
        build_finding_disposition(
            finding_id=item.finding_id,
            disposition="APPROVED",
            basis="governed direct fact",
            approved_evidence_ids=item.evidence_ids,
            confidence=1.0,
        )
        for item in findings
    )
    packet = build_approved_response_packet(
        packet_id="packet-1",
        approved_finding_ids=tuple(item.finding_id for item in findings),
        approved_evidence_ids=tuple(
            dict.fromkeys(
                evidence_id
                for item in findings
                for evidence_id in item.evidence_ids
            )
        ),
    )
    return build_decision_output(
        request_id="request-1",
        decision_id="decision-1",
        decision="APPROVED",
        finding_dispositions=dispositions,
        response_packet=packet,
        confidence=1.0,
    )


def test_primary_direct_fact_becomes_explicit_direct_answer_section() -> None:
    source = _source(component_ids=("obligation_value", "exception_condition"))
    packages, _ = materialize_published_requirement(
        source=source,
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
    decision = _decision_for_findings(findings)
    explanation_input = build_explanation_input(
        request_id="request-1",
        decision_output=decision,
    )
    style = build_style_definition(
        style_id="customer-simple-v1",
        style_version="1.0",
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_modes=("PLAIN_LANGUAGE",),
    )
    rendered = render_explanation_templates(
        explanation_input=explanation_input,
        findings_by_id={item.finding_id: item for item in findings},
        style=style,
    )

    direct = [item for item in rendered.sections if item.section_type == "DIRECT_ANSWER"]
    meaning = [item for item in rendered.sections if item.section_type == "MEANING"]
    assert [item.text for item in direct] == ["The obligation is 20%."]
    assert any("documented waiver" in item.text for item in meaning)


def test_requested_component_drives_primary_role_when_multiple_required_are_published() -> None:
    source = _source(component_ids=("obligation_value", "trigger_condition"))

    packages, _ = materialize_published_requirement(
        source=source,
        requirement_id="runtime-req",
        subject_reference="requested_fact",
        requested_semantic_component="trigger_condition",
    )

    roles = {item.field_or_topic: _role(item) for item in packages}
    assert roles == {
        "OBLIGATION_VALUE": "QUALIFYING",
        "TRIGGER_CONDITION": "PRIMARY",
    }
