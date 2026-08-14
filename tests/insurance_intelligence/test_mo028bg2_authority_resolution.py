from datetime import date

import pytest

from insurance_intelligence.generic_knowledge.authority_resolution import (
    AuthorityCandidate,
    AuthorityClass,
    AuthorityResolutionError,
    AuthorityResolutionStatus,
    authority_rank,
    blocker_for_authority_resolution,
    resolve_authority_candidates,
)
from insurance_intelligence.generic_knowledge.contracts import (
    ApplicabilityKey,
    EvidenceReference,
    PublicationBlockerCode,
)


def _app(**kwargs):
    return ApplicabilityKey(product_reference="pv_test_product", **kwargs)


def _evidence(evidence_id: str, authority: AuthorityClass) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=evidence_id,
        source_document_id=f"doc_{evidence_id}",
        source_document_version="v1",
        source_hash_sha256=f"sha_{evidence_id}",
        locator="page:1",
        authority_class=authority.value,
    )


def _candidate(
    candidate_id: str,
    authority: AuthorityClass,
    value: dict,
    *,
    effective_from=None,
    effective_to=None,
    applicability=None,
):
    return AuthorityCandidate(
        candidate_id=candidate_id,
        concept="waiting_periods",
        semantic_key="ped_duration",
        semantic_value=value,
        applicability=applicability or _app(),
        evidence=_evidence(candidate_id, authority),
        authority_class=authority,
        effective_from=effective_from,
        effective_to=effective_to,
    )


def test_authority_rank_places_regulation_above_policy_wording() -> None:
    assert authority_rank(AuthorityClass.REGULATORY_OVERLAY) > authority_rank(
        AuthorityClass.POLICY_WORDING
    )
    assert authority_rank(AuthorityClass.POLICY_WORDING) > authority_rank(
        AuthorityClass.CUSTOMER_INFORMATION_SHEET
    )
    assert authority_rank(AuthorityClass.CUSTOMER_INFORMATION_SHEET) > authority_rank(
        AuthorityClass.PROSPECTUS
    )
    assert authority_rank(AuthorityClass.PROSPECTUS) > authority_rank(
        AuthorityClass.BROCHURE
    )


def test_policy_wording_wins_over_lower_authority_product_sources() -> None:
    result = resolve_authority_candidates(
        [
            _candidate("brochure", AuthorityClass.BROCHURE, {"value": 24, "unit": "MONTHS"}),
            _candidate("wording", AuthorityClass.POLICY_WORDING, {"value": 36, "unit": "MONTHS"}),
        ],
        concept="waiting_periods",
        semantic_key="ped_duration",
        as_of_date=date(2026, 8, 9),
    )
    assert result.status is AuthorityResolutionStatus.RESOLVED
    assert result.selected_candidate_ids == ("wording",)
    assert result.semantic_value == {"value": 36, "unit": "MONTHS"}
    assert "brochure" in result.rejected_candidate_ids


def test_equal_authority_same_value_is_corroborating_not_conflict() -> None:
    result = resolve_authority_candidates(
        [
            _candidate("wording_a", AuthorityClass.POLICY_WORDING, {"value": 36, "unit": "MONTHS"}),
            _candidate("wording_b", AuthorityClass.POLICY_WORDING, {"value": 36, "unit": "MONTHS"}),
        ],
        concept="waiting_periods",
        semantic_key="ped_duration",
        as_of_date=date(2026, 8, 9),
    )
    assert result.status is AuthorityResolutionStatus.RESOLVED
    assert result.selected_candidate_ids == ("wording_a", "wording_b")


def test_equal_authority_different_values_fail_closed() -> None:
    result = resolve_authority_candidates(
        [
            _candidate("wording_a", AuthorityClass.POLICY_WORDING, {"value": 36, "unit": "MONTHS"}),
            _candidate("wording_b", AuthorityClass.POLICY_WORDING, {"value": 48, "unit": "MONTHS"}),
        ],
        concept="waiting_periods",
        semantic_key="ped_duration",
        as_of_date=date(2026, 8, 9),
    )
    assert result.status is AuthorityResolutionStatus.CONFLICTED
    assert result.semantic_value is None
    blocker = blocker_for_authority_resolution(result, applicability=_app())
    assert blocker is not None
    assert blocker.code is PublicationBlockerCode.AUTHORITY_CONFLICT


def test_regulatory_overlay_wins_without_mutating_lower_contract_candidate() -> None:
    contract = _candidate(
        "wording",
        AuthorityClass.POLICY_WORDING,
        {"value": 48, "unit": "MONTHS"},
    )
    overlay = _candidate(
        "regulation",
        AuthorityClass.REGULATORY_OVERLAY,
        {"value": 36, "unit": "MONTHS", "operation": "CEILING"},
    )
    result = resolve_authority_candidates(
        [contract, overlay],
        concept="waiting_periods",
        semantic_key="ped_duration",
        as_of_date=date(2026, 8, 9),
    )
    assert result.status is AuthorityResolutionStatus.RESOLVED
    assert result.regulatory_overlay_applied is True
    assert result.selected_candidate_ids == ("regulation",)
    assert contract.semantic_value == {"value": 48, "unit": "MONTHS"}


def test_regulatory_overlay_is_date_sensitive() -> None:
    overlay = _candidate(
        "regulation",
        AuthorityClass.REGULATORY_OVERLAY,
        {"value": 36, "unit": "MONTHS", "operation": "CEILING"},
        effective_from=date(2024, 4, 1),
    )
    wording = _candidate(
        "wording",
        AuthorityClass.POLICY_WORDING,
        {"value": 48, "unit": "MONTHS"},
    )
    before = resolve_authority_candidates(
        [overlay, wording],
        concept="waiting_periods",
        semantic_key="ped_duration",
        as_of_date=date(2024, 3, 31),
    )
    after = resolve_authority_candidates(
        [overlay, wording],
        concept="waiting_periods",
        semantic_key="ped_duration",
        as_of_date=date(2024, 4, 1),
    )
    assert before.selected_candidate_ids == ("wording",)
    assert after.selected_candidate_ids == ("regulation",)


def test_applicability_effective_dates_filter_candidates() -> None:
    old = _candidate(
        "old",
        AuthorityClass.POLICY_WORDING,
        {"value": 48, "unit": "MONTHS"},
        applicability=_app(effective_to=date(2025, 12, 31)),
    )
    new = _candidate(
        "new",
        AuthorityClass.POLICY_WORDING,
        {"value": 36, "unit": "MONTHS"},
        applicability=_app(effective_from=date(2026, 1, 1)),
    )
    result = resolve_authority_candidates(
        [old, new],
        concept="waiting_periods",
        semantic_key="ped_duration",
        as_of_date=date(2026, 8, 9),
    )
    assert result.selected_candidate_ids == ("new",)
    assert "old" in result.rejected_candidate_ids


def test_no_applicable_candidate_blocks_publication() -> None:
    result = resolve_authority_candidates(
        [
            _candidate(
                "future",
                AuthorityClass.POLICY_WORDING,
                {"value": 36, "unit": "MONTHS"},
                effective_from=date(2027, 1, 1),
            )
        ],
        concept="waiting_periods",
        semantic_key="ped_duration",
        as_of_date=date(2026, 8, 9),
    )
    assert result.status is AuthorityResolutionStatus.NO_APPLICABLE_CANDIDATE
    blocker = blocker_for_authority_resolution(result, applicability=_app())
    assert blocker is not None
    assert blocker.code is PublicationBlockerCode.REVIEW_REQUIRED


def test_conflicting_regulatory_overlays_use_regulatory_conflict_blocker() -> None:
    result = resolve_authority_candidates(
        [
            _candidate("reg_a", AuthorityClass.REGULATORY_OVERLAY, {"value": 36, "unit": "MONTHS"}),
            _candidate("reg_b", AuthorityClass.REGULATORY_OVERLAY, {"value": 24, "unit": "MONTHS"}),
        ],
        concept="waiting_periods",
        semantic_key="ped_duration",
        as_of_date=date(2026, 8, 9),
    )
    blocker = blocker_for_authority_resolution(result, applicability=_app())
    assert blocker is not None
    assert blocker.code is PublicationBlockerCode.REGULATORY_CONFLICT


def test_authority_candidate_requires_evidence_authority_match() -> None:
    with pytest.raises(AuthorityResolutionError):
        AuthorityCandidate(
            candidate_id="bad",
            concept="waiting_periods",
            semantic_key="ped_duration",
            semantic_value={"value": 36},
            applicability=_app(),
            evidence=_evidence("bad", AuthorityClass.BROCHURE),
            authority_class=AuthorityClass.POLICY_WORDING,
        )


def test_resolved_authority_has_no_publication_blocker() -> None:
    result = resolve_authority_candidates(
        [_candidate("wording", AuthorityClass.POLICY_WORDING, {"value": 36, "unit": "MONTHS"})],
        concept="waiting_periods",
        semantic_key="ped_duration",
        as_of_date=date(2026, 8, 9),
    )
    assert blocker_for_authority_resolution(result, applicability=_app()) is None
