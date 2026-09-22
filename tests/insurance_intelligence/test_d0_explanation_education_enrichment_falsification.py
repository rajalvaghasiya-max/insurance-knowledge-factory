from __future__ import annotations

from insurance_intelligence.contracts.decision import (
    build_approved_response_packet,
    build_finding_disposition,
    build_output as build_decision_output,
)
from insurance_intelligence.contracts.education_publication import (
    CUSTOMER_EDUCATION,
    EDUCATION_PUBLICATION_STATUS,
    EducationExample,
    EducationPublicationRecord,
)
from insurance_intelligence.contracts.explanation import build_input


def _decision():
    packet = build_approved_response_packet(
        packet_id="packet-education-falsification",
        approved_finding_ids=("finding-1",),
        approved_evidence_ids=("product-evidence-1",),
        limitation_ids=(),
        prohibited_operations=("RECOMMEND",),
    )
    disposition = build_finding_disposition(
        finding_id="finding-1",
        disposition="APPROVED",
        basis="Supported by governed product evidence.",
        approved_evidence_ids=("product-evidence-1",),
        confidence=0.95,
    )
    return build_decision_output(
        request_id="request-education-falsification",
        decision_id="decision-education-falsification",
        decision="APPROVED",
        finding_dispositions=(disposition,),
        response_packet=packet,
        confidence=0.95,
    )


def _education_publication() -> EducationPublicationRecord:
    return EducationPublicationRecord(
        contract_version="1.0",
        publication_id="education-publication-waiting-period-v1",
        publication_status=EDUCATION_PUBLICATION_STATUS,
        allowed_uses=(CUSTOMER_EDUCATION,),
        concept_id="waiting_period",
        canonical_name="Waiting Period",
        definition="A waiting period is a policy-defined period.",
        plain_language_explanation=(
            "Some policy benefits or conditions may not become available immediately."
        ),
        practical_implication=(
            "The applicable policy rule must be checked before applying the concept "
            "to a specific customer situation."
        ),
        examples=(
            EducationExample(
                scenario="A policy contains a waiting-period clause.",
                result="That restriction can apply during the governed period.",
                boundary=(
                    "Illustrative only. This does not determine claim approval or payment."
                ),
            ),
        ),
        limitations=("Generic education only.",),
        product_specific_boundary=(
            "Product duration, scope and exceptions require governed product evidence."
        ),
        customer_document_boundary=(
            "Customer dates and selections require applicable customer documents."
        ),
        evidence_references=("education-evidence-1",),
        source_asset_id="meaning-waiting-period-v1",
        source_asset_digest="a" * 64,
        source_governed_record_id="gconcept-waiting-period-v1",
        source_knowledge_version="1.0",
        review_decision_id="review-waiting-period-v1",
        publication_authority="PolicyScna education publication gate",
        publication_receipt_id="education-receipt-waiting-period-v1",
    )


def test_explanation_input_accepts_typed_published_education_separately_from_decision_authority() -> None:
    decision = _decision()
    education = _education_publication()

    item = build_input(
        request_id="request-education-falsification",
        decision_output=decision,
        education_publications=(education,),
        communication_context={"domain_scope": "HEALTH"},
    )

    assert item.education_publications == (education,)
    assert item.decision_output is decision
    assert item.decision_output.response_packet is not None
    assert item.decision_output.response_packet.approved_finding_ids == ("finding-1",)
    assert item.decision_output.response_packet.approved_evidence_ids == (
        "product-evidence-1",
    )
    assert education.publication_receipt_id not in (
        item.decision_output.response_packet.approved_evidence_ids
    )
