from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from insurance_intelligence.rule_certification.runner import run_rule_certification
from insurance_intelligence.rule_certification.star_health_initial_waiting_period import (
    STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_CANDIDATE_ID,
    STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_EVIDENCE_HASH,
    STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_REVIEWED_STATEMENT,
    STAR_COMPREHENSIVE_POLICY_WORDING_SHA256,
    STAR_COMPREHENSIVE_SOURCE_REGISTRATION_PATH,
    STAR_COMPREHENSIVE_SOURCE_REGISTRATION_SHA256,
    build_star_comprehensive_initial_waiting_period_case,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = (
    REPOSITORY_ROOT
    / "docs/architecture/STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_MANUFACTURING_SPEC.json"
)


def _run(case):
    return run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
    )


def _spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _source_page() -> dict:
    registration = json.loads(
        (REPOSITORY_ROOT / STAR_COMPREHENSIVE_SOURCE_REGISTRATION_PATH).read_text(
            encoding="utf-8"
        )
    )
    return next(
        item
        for item in registration["evidence_review"]["candidates"]
        if item["candidate_id"] == STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_CANDIDATE_ID
    )


def test_case_passes_unchanged_generic_waiting_period_runner() -> None:
    case = build_star_comprehensive_initial_waiting_period_case()
    result = _run(case)

    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert result.failures == ()
    assert all(check.passed for check in result.component_checks)


def test_case_uses_the_existing_six_component_waiting_period_topic() -> None:
    case = build_star_comprehensive_initial_waiting_period_case()

    assert case.expectation.topic_id == "waiting_period"
    assert case.expectation.topic_version == "1.0"
    assert tuple(item.component_id for item in case.expectation.component_expectations) == (
        "waiting_period_duration",
        "waiting_period_subject",
        "start_basis",
        "applicability_scope",
        "continuity_or_credit_rule",
        "exception_condition",
    )


def test_case_is_bound_to_registered_current_page_32_evidence() -> None:
    case = build_star_comprehensive_initial_waiting_period_case()
    source_page = _source_page()

    assert source_page["source_page"] == 32
    assert source_page["text_sha256"] == STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_EVIDENCE_HASH
    for package in case.evidence_output.evidence_packages:
        assert package.page == 32
        assert package.source_type == "POLICY_WORDING"
        assert package.source_excerpt == STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_REVIEWED_STATEMENT
        assert package.lineage.source_artifact_sha256 == STAR_COMPREHENSIVE_POLICY_WORDING_SHA256
        assert package.lineage.governed_record_sha256 == STAR_COMPREHENSIVE_SOURCE_REGISTRATION_SHA256
        assert package.lineage.binding_reference.endswith(
            STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_CANDIDATE_ID
        )


def test_every_manufactured_component_is_reproducible_from_registered_source() -> None:
    page_text = _source_page()["excerpt"]

    for component in _spec()["source_proven_components"]:
        for fragment in component["required_fragments"]:
            assert _normalized(fragment) in _normalized(page_text), (
                component["component_id"],
                fragment,
            )


def test_rule_preserves_duration_subject_start_scope_continuity_and_exception() -> None:
    case = build_star_comprehensive_initial_waiting_period_case()
    claims = {
        package.field_or_topic: package.claim
        for package in case.evidence_output.evidence_packages
    }

    assert "30 days" in claims["WAITING_PERIOD_DURATION"]
    assert "any illness" in claims["WAITING_PERIOD_SUBJECT"]
    assert "first policy commencement date" in claims["WAITING_PERIOD_START_BASIS"]
    assert "enhanced Sum Insured" in claims["APPLICABILITY_SCOPE"]
    assert "more than twelve months" in claims["CONTINUITY_OR_CREDIT_RULE"]
    assert "provided the same are covered" in claims["EXCEPTION_CONDITION"]


def test_boundary_convention_and_claim_outcome_remain_unmanufactured() -> None:
    case = build_star_comprehensive_initial_waiting_period_case()
    serialized = repr(case)
    decision = _spec()["decision"]

    assert "ON_OR_AFTER_CALCULATED_DATE" not in serialized
    assert "AFTER_COMPLETION_OF_PERIOD" not in serialized
    assert "first_active_date" not in serialized
    assert decision["new_timeline_convention"] == "NOT_AUTHORIZED"
    assert decision["customer_facing_publication"] == "NOT_AUTHORIZED_BY_THIS_MILESTONE"


def test_safety_limitations_preserve_policy_instance_and_claim_boundaries() -> None:
    case = build_star_comprehensive_initial_waiting_period_case()
    limitations = " ".join(case.evidence_output.limitations).lower()

    assert "does not itself publish" in limitations
    assert "exact first-active calendar date" in limitations
    assert "otherwise covered" in limitations
    assert "policy schedule" in limitations
    assert "endorsements" in limitations
    assert "does not guarantee claim approval or payment" in limitations


def test_missing_required_duration_fails_closed() -> None:
    case = build_star_comprehensive_initial_waiting_period_case()
    requirement_id = (
        "requirement:star-comprehensive-initial-waiting-period:waiting_period_duration"
    )
    requirements = tuple(
        replace(
            item,
            status="MISSING",
            matched_evidence_ids=(),
            missing_reason="duration removed by mutation",
            authority_satisfied=False,
            version_satisfied=False,
            lineage_satisfied=False,
            confidence=0.0,
        )
        if item.requirement_id == requirement_id
        else item
        for item in case.evidence_output.requirement_results
    )
    mutated = replace(
        case,
        evidence_output=replace(case.evidence_output, requirement_results=requirements),
    )

    result = _run(mutated)

    assert result.outcome != "PASS"
    assert result.actual_explanation_permitted is False


def test_case_is_deterministic_and_immutable() -> None:
    first = build_star_comprehensive_initial_waiting_period_case()
    second = build_star_comprehensive_initial_waiting_period_case()

    assert first == second
    try:
        first.case_id = "changed"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("certification fixture must remain immutable")
