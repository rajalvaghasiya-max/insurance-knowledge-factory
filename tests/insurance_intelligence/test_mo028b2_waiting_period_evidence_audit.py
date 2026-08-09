from pathlib import Path

from insurance_intelligence.benefits.waiting_period_contracts import WaitingPeriodType
from insurance_intelligence.benefits.waiting_period_evidence_audit import (
    EvidenceAuditStatus,
    audit_all_waiting_period_candidates,
    audit_waiting_period_candidates,
    load_registered_source,
)


REGISTERED_SOURCE = Path(
    "knowledge/factory/registry_backed/star_health_star_comprehensive/"
    "generic_source_registration/policy_wording_registration.json"
)
EXPECTED_DOCUMENT_SHA256 = (
    "b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f"
)


def _source():
    return load_registered_source(REGISTERED_SOURCE)


def test_registered_star_policy_wording_is_the_exact_governed_document_version():
    result = audit_waiting_period_candidates(_source(), WaitingPeriodType.INITIAL)
    assert result.document_id == "star_health_star_comprehensive_policy_wording_v1"
    assert result.document_version_id == (
        "docver_star_health_star_comprehensive_policy_wording_v1_b1dbe8fb78646f75"
    )
    assert result.document_sha256 == EXPECTED_DOCUMENT_SHA256
    assert result.storage_locator == (
        "archive/raw_documents/star_health/star_comprehensive_policy_wording_2025.pdf"
    )


def test_initial_waiting_period_candidate_is_isolated_but_not_auto_approved():
    result = audit_waiting_period_candidates(_source(), WaitingPeriodType.INITIAL)
    assert result.marker == "Code Excl 03"
    assert result.status is EvidenceAuditStatus.REVIEW_REQUIRED
    assert result.candidates
    assert any("30-day waiting period" in item.excerpt for item in result.candidates)
    assert all("Code Excl 03" in item.excerpt for item in result.candidates)


def test_specific_disease_waiting_period_candidates_require_review():
    result = audit_waiting_period_candidates(
        _source(), WaitingPeriodType.SPECIFIC_DISEASE_PROCEDURE
    )
    assert result.marker == "Code Excl 02"
    assert result.status is EvidenceAuditStatus.REVIEW_REQUIRED
    assert result.candidates
    assert all("Code Excl 02" in item.excerpt for item in result.candidates)


def test_pre_existing_disease_candidates_require_review_and_are_not_collapsed():
    result = audit_waiting_period_candidates(
        _source(), WaitingPeriodType.PRE_EXISTING_DISEASE
    )
    assert result.marker == "Code Excl 01"
    assert result.status is EvidenceAuditStatus.REVIEW_REQUIRED
    assert result.candidates
    assert all("Code Excl 01" in item.excerpt for item in result.candidates)
    # Multiple occurrences are valid because base and optional-cover text can repeat
    # the same exclusion code. The audit must preserve every candidate for review.
    assert len({item.candidate_id for item in result.candidates}) == len(result.candidates)


def test_all_three_waiting_period_types_are_audited_without_publication():
    results = audit_all_waiting_period_candidates(_source())
    assert tuple(item.waiting_period_type for item in results) == (
        WaitingPeriodType.INITIAL,
        WaitingPeriodType.SPECIFIC_DISEASE_PROCEDURE,
        WaitingPeriodType.PRE_EXISTING_DISEASE,
    )
    assert all(item.status is EvidenceAuditStatus.REVIEW_REQUIRED for item in results)
    assert all(item.candidates for item in results)
    assert not hasattr(results[0], "mechanic")
    assert not hasattr(results[0], "publication_status")
