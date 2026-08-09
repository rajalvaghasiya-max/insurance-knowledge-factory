from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.rule_certification.runner import run_rule_certification
from insurance_intelligence.rule_certification.star_health_room_rent import (
    STAR_COMPREHENSIVE_POLICY_WORDING_SHA256,
    STAR_COMPREHENSIVE_ROOM_RENT_CANDIDATE_ID,
    STAR_COMPREHENSIVE_ROOM_RENT_EVIDENCE_HASH,
    STAR_COMPREHENSIVE_ROOM_RENT_SOURCE_EXCERPT,
    build_star_comprehensive_room_rent_case,
)


def test_star_room_rent_case_runs_to_complete_pass() -> None:
    case = build_star_comprehensive_room_rent_case()

    result = run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
    )

    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert result.failures == ()
    assert all(check.passed for check in result.component_checks)


def test_star_room_rent_case_certifies_coverage_limit_semantics() -> None:
    case = build_star_comprehensive_room_rent_case()

    assert case.expectation.topic_id == "coverage_limit"
    assert case.expectation.topic_version == "1.0"
    assert tuple(
        expectation.component_id
        for expectation in case.expectation.component_expectations
    ) == (
        "covered_subject",
        "limit_value",
        "limit_basis",
        "applicability_scope",
        "excess_consequence",
    )


def test_star_room_rent_case_preserves_exact_primary_source_trace() -> None:
    case = build_star_comprehensive_room_rent_case()

    assert len(case.evidence_output.evidence_packages) == 5
    for evidence in case.evidence_output.evidence_packages:
        assert evidence.source_type == "POLICY_WORDING"
        assert evidence.page == 9
        assert evidence.section == "II.1 In-patient Treatment"
        assert STAR_COMPREHENSIVE_ROOM_RENT_CANDIDATE_ID in evidence.retrieval_basis
        assert evidence.lineage.source_artifact_sha256 == STAR_COMPREHENSIVE_POLICY_WORDING_SHA256
        assert evidence.lineage.governed_record_sha256 == STAR_COMPREHENSIVE_ROOM_RENT_EVIDENCE_HASH
        assert evidence.source_excerpt == STAR_COMPREHENSIVE_ROOM_RENT_SOURCE_EXCERPT


def test_star_room_rent_case_does_not_invent_monetary_cap() -> None:
    case = build_star_comprehensive_room_rent_case()
    claims = " ".join(
        evidence.claim for evidence in case.evidence_output.evidence_packages
    ).lower()

    assert "private single a/c room" in claims
    assert "no separate monetary room-rent cap" in claims
    assert "whichever is less" in claims
    assert "per day" not in claims
    assert "₹" not in claims
    assert "rs." not in claims


def test_star_room_rent_case_keeps_scope_and_consequence_distinct() -> None:
    case = build_star_comprehensive_room_rent_case()
    claims = {
        evidence.field_or_topic: evidence.claim
        for evidence in case.evidence_output.evidence_packages
    }

    assert "hospitalization expenses that vary" in claims["APPLICABILITY_SCOPE"]
    assert "considered proportionately" in claims["EXCESS_CONSEQUENCE"]
    assert claims["APPLICABILITY_SCOPE"] != claims["EXCESS_CONSEQUENCE"]


def test_star_room_rent_case_preserves_safety_limitations() -> None:
    case = build_star_comprehensive_room_rent_case()
    limitations = " ".join(case.evidence_output.limitations).lower()

    assert "does not itself publish" in limitations
    assert "room category" in limitations
    assert "does not guarantee" in limitations
    assert "payment" in limitations


def test_star_room_rent_case_is_materially_different_from_copayment() -> None:
    case = build_star_comprehensive_room_rent_case()
    combined = " ".join(
        evidence.claim for evidence in case.evidence_output.evidence_packages
    ).lower()

    assert case.expectation.topic_id == "coverage_limit"
    assert "co-payment" not in combined
    assert "entry age" not in combined
    assert "61" not in combined


def test_star_room_rent_fixture_is_immutable() -> None:
    case = build_star_comprehensive_room_rent_case()

    with pytest.raises(FrozenInstanceError):
        case.case_id = "changed"  # type: ignore[misc]
