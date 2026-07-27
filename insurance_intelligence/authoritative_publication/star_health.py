"""Star Comprehensive authoritative-publication pilot records (P2.4)."""

from __future__ import annotations

from insurance_intelligence.authoritative_publication.gate import (
    create_authoritative_publication,
)
from insurance_intelligence.contracts.authoritative_publication import (
    AuthoritativePublicationRecord,
    build_authoritative_publication_input,
    build_governed_publication_projection,
    build_governed_semantic_component,
)
from insurance_intelligence.publication_decision.star_health import (
    build_star_bariatric_surgery_publication_decision,
    build_star_conditional_copayment_publication_decision,
    build_star_room_rent_publication_decision,
)
from insurance_intelligence.rule_certification.star_health_bariatric_surgery import (
    build_star_comprehensive_bariatric_surgery_case,
)
from insurance_intelligence.rule_certification.star_health_room_rent import (
    build_star_comprehensive_room_rent_case,
)

PUBLICATION_AUTHORITY = "P2.4 governed authoritative publication authority"


def _projection_from_case(*, projection_id: str, decision, case):
    evidence_by_component: dict[str, tuple[str, ...]] = {}
    for component in case.expectation.component_expectations:
        suffix = f":{component.component_id}"
        matches = tuple(
            item.evidence_id
            for item in case.evidence_output.evidence_packages
            if item.normalized_fact_reference.endswith(suffix)
            or item.evidence_id.endswith(suffix)
        )
        evidence_by_component[component.component_id] = matches

    return build_governed_publication_projection(
        projection_id=projection_id,
        governed_subject_reference=decision.governed_subject_reference,
        certification_id=decision.certification_id,
        topic_id=decision.topic_id,
        topic_version=decision.topic_version,
        semantic_components=tuple(
            build_governed_semantic_component(
                component_id=component.component_id,
                status="SATISFIED",
                evidence_references=evidence_by_component[component.component_id],
            )
            for component in case.expectation.component_expectations
        ),
        limitations=decision.limitations,
        evidence_trace_references=decision.evidence_trace_references,
        certification_trace_references=decision.certification_trace_references,
    )


def build_star_room_rent_authoritative_publication() -> AuthoritativePublicationRecord:
    decision = build_star_room_rent_publication_decision()
    case = build_star_comprehensive_room_rent_case()
    projection = _projection_from_case(
        projection_id="publication-projection:star-comprehensive:room-rent",
        decision=decision,
        case=case,
    )
    return create_authoritative_publication(
        build_authoritative_publication_input(
            publication_id="authoritative-publication:star-comprehensive:room-rent",
            publication_decision=decision,
            governed_projection=projection,
            publication_authority=PUBLICATION_AUTHORITY,
        )
    )


def build_star_bariatric_surgery_authoritative_publication() -> AuthoritativePublicationRecord:
    decision = build_star_bariatric_surgery_publication_decision()
    case = build_star_comprehensive_bariatric_surgery_case()
    projection = _projection_from_case(
        projection_id="publication-projection:star-comprehensive:bariatric-surgery",
        decision=decision,
        case=case,
    )
    return create_authoritative_publication(
        build_authoritative_publication_input(
            publication_id="authoritative-publication:star-comprehensive:bariatric-surgery",
            publication_decision=decision,
            governed_projection=projection,
            publication_authority=PUBLICATION_AUTHORITY,
        )
    )


def build_star_conditional_copayment_authoritative_publication() -> AuthoritativePublicationRecord:
    """Attempting publication must fail because P2.3 explicitly WITHHOLDS it."""
    decision = build_star_conditional_copayment_publication_decision()
    case = build_star_comprehensive_room_rent_case()
    projection = _projection_from_case(
        projection_id="publication-projection:star-comprehensive:conditional-copayment",
        decision=decision,
        case=case,
    )
    return create_authoritative_publication(
        build_authoritative_publication_input(
            publication_id="authoritative-publication:star-comprehensive:conditional-copayment",
            publication_decision=decision,
            governed_projection=projection,
            publication_authority=PUBLICATION_AUTHORITY,
        )
    )
