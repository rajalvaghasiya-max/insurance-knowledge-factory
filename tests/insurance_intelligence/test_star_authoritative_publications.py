from __future__ import annotations

import pytest

from insurance_intelligence.authoritative_publication.gate import (
    AuthoritativePublicationGateError,
)
from insurance_intelligence.authoritative_publication.star_health import (
    build_star_bariatric_surgery_authoritative_publication,
    build_star_conditional_copayment_authoritative_publication,
    build_star_room_rent_authoritative_publication,
)


def test_room_rent_creates_authoritative_publication():
    result = build_star_room_rent_authoritative_publication()
    assert result.publication_status == "AUTHORITATIVE"
    assert result.topic_id == "coverage_limit"
    assert result.certification_id == "star_comprehensive_room_rent"
    assert {item.component_id for item in result.semantic_components} == {
        "covered_subject",
        "limit_value",
        "limit_basis",
        "applicability_scope",
        "excess_consequence",
    }
    assert any("not a separate monetary room-rent cap" in item for item in result.limitations)
    assert any("does not guarantee admissibility or payment" in item for item in result.limitations)


def test_bariatric_creates_authoritative_publication():
    result = build_star_bariatric_surgery_authoritative_publication()
    assert result.publication_status == "AUTHORITATIVE"
    assert result.topic_id == "eligibility_and_consequence"
    assert result.certification_id == "star_comprehensive_bariatric_surgery"
    assert {item.component_id for item in result.semantic_components} == {
        "eligibility_criteria",
        "applicability_scope",
        "eligible_consequence",
        "ineligible_consequence",
        "exception_condition",
    }
    assert any("does not decide individual medical suitability" in item for item in result.limitations)
    assert any("does not guarantee claim admissibility or payment" in item for item in result.limitations)


def test_conditional_copayment_withhold_cannot_cross_publication_gate():
    with pytest.raises(AuthoritativePublicationGateError, match="Only a PUBLISH"):
        build_star_conditional_copayment_authoritative_publication()


def test_star_publications_preserve_exact_evidence_and_certification_trace():
    for result in (
        build_star_room_rent_authoritative_publication(),
        build_star_bariatric_surgery_authoritative_publication(),
    ):
        assert result.certification_trace_references
        assert result.evidence_trace_references
        component_evidence = {
            evidence
            for component in result.semantic_components
            for evidence in component.evidence_references
        }
        assert component_evidence == set(result.evidence_trace_references)


def test_star_publication_records_are_deterministic():
    assert (
        build_star_room_rent_authoritative_publication()
        == build_star_room_rent_authoritative_publication()
    )
    assert (
        build_star_bariatric_surgery_authoritative_publication()
        == build_star_bariatric_surgery_authoritative_publication()
    )


def test_star_publications_do_not_expose_claim_or_recommendation_outputs():
    for result in (
        build_star_room_rent_authoritative_publication(),
        build_star_bariatric_surgery_authoritative_publication(),
    ):
        for field in (
            "final_answer",
            "explanation",
            "recommendation",
            "medical_suitability",
            "claim_decision",
            "claim_payment",
        ):
            assert not hasattr(result, field)
