from __future__ import annotations

import copy

import pytest

from knowledge_domains.health.extraction_primitives.governed_fact_selection import (
    GovernedFactSelectionContract,
    GovernedFactSelectionError,
)
from knowledge_domains.health.extraction_primitives.reviewer_decision_record import ReviewerDecisionRecordContract
from knowledge_domains.health.extraction_primitives.reviewer_decision_submission import ReviewerDecisionSubmissionContract

SHA = "a" * 64
SOURCE = {
    "entity_id": "example:product",
    "insurer_id": "example",
    "document_type": "policy_wording",
    "source_document_id": "sha256:" + SHA,
    "sha256": SHA,
    "source_url": "https://example.test/policy.pdf",
    "source_page_url": "https://example.test/product",
    "relative_archive_path": "archive/raw_pdf/example/policy.pdf",
    "provenance_status": "download_registry_verified",
}


def _review_group(group_id: str, value: int):
    return {
        "group_id": group_id,
        "candidate_type": "currency_amount",
        "normalized_value": {"kind": "currency", "value": value, "unit": "INR"},
        "inferred_scope": {"benefit_scope_key": "example_benefit", "band_scope_key": None},
        "review_flags": ["role_selection_required"],
        "supporting_candidates": [{"candidate_id": "excand_" + group_id}],
    }


def _submission(*, role: str = "sub_limit_or_limit", decision: str = "accept"):
    review = {
        "schema_version": "1.0",
        "review_type": "health_currency_candidate_review_document_v1",
        "review_layer": "currency_candidate_review",
        "review_layer_version": "1.0",
        "status": "review_records_generated",
        "source": SOURCE,
        "review_group_count": 1,
        "review_groups": [_review_group("crgrp_example", 50000)],
    }
    pending = ReviewerDecisionRecordContract.build_pending_document(review)
    record = pending["decision_records"][0]
    if decision == "accept":
        pending["decision_records"][0] = ReviewerDecisionRecordContract.build_resolved_record(
            record,
            decision="accept",
            reviewer_identity="reviewer@example.test",
            reviewed_at="2026-07-05T12:00:00Z",
            review_rationale="Reviewed the bounded clause and source-linked evidence.",
            selected_role=role,
            selected_benefit_scope="example_benefit",
            selected_band_scope=None,
        )
    else:
        pending["decision_records"][0] = ReviewerDecisionRecordContract.build_resolved_record(
            record,
            decision=decision,
            reviewer_identity="reviewer@example.test",
            reviewed_at="2026-07-05T12:00:00Z",
            review_rationale="Deferred pending field-registry policy.",
        )
    pending["status"] = "completed_human_review"
    return ReviewerDecisionSubmissionContract.build_submission_document(
        pending,
        submitted_by="submitter@example.test",
        submitted_at="2026-07-05T12:30:00Z",
    )


def test_selects_supported_accepted_currency_sub_limit_without_publication():
    result = GovernedFactSelectionContract.build_selection_document(
        _submission(), selector_identity="selector@example.test", selected_at="2026-07-05T13:00:00Z"
    )
    record = result["selection_records"][0]
    assert result["status"] == "selection_completed_not_published"
    assert result["publication_state"] == "not_published"
    assert result["entitlement_state"] == "not_evaluated"
    assert record["selection_status"] == "selected_governed_fact"
    assert record["canonical_field_key"] == "currency_sub_limit"
    assert record["governed_fact_id"].startswith("gfact_")


def test_defers_accepted_premium_until_field_registry_defines_it():
    result = GovernedFactSelectionContract.build_selection_document(
        _submission(role="premium"), selector_identity="selector@example.test", selected_at="2026-07-05T13:00:00Z"
    )
    record = result["selection_records"][0]
    assert record["selection_status"] == "deferred"
    assert record["canonical_field_key"] is None
    assert record["governed_fact_id"] is None


def test_blocks_rejected_review_record():
    result = GovernedFactSelectionContract.build_selection_document(
        _submission(decision="reject"), selector_identity="selector@example.test", selected_at="2026-07-05T13:00:00Z"
    )
    assert result["selection_records"][0]["selection_status"] == "blocked"


def test_rejects_invalid_submission_status():
    bad = _submission()
    bad["status"] = "draft"
    with pytest.raises(GovernedFactSelectionError, match="submission status"):
        GovernedFactSelectionContract.build_selection_document(
            bad, selector_identity="selector@example.test", selected_at="2026-07-05T13:00:00Z"
        )


def test_rejects_tampered_selection_that_claims_publication():
    result = GovernedFactSelectionContract.build_selection_document(
        _submission(), selector_identity="selector@example.test", selected_at="2026-07-05T13:00:00Z"
    )
    tampered = copy.deepcopy(result)
    tampered["selection_records"][0]["publication_state"] = "published"
    with pytest.raises(GovernedFactSelectionError, match="unpublished"):
        GovernedFactSelectionContract.validate_selection_document(tampered)
