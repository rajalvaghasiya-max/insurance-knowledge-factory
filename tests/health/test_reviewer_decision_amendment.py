from __future__ import annotations

import copy

import pytest

from knowledge_domains.health.extraction_primitives.reviewer_decision_amendment import (
    ReviewerDecisionAmendmentError,
    ReviewerDecisionAmendmentWorkflow,
)
from knowledge_domains.health.extraction_primitives.reviewer_decision_record import (
    ReviewerDecisionRecordContract,
)

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


def completed_document():
    review = {
        "schema_version": "1.0",
        "review_type": "health_currency_candidate_review_document_v1",
        "review_layer": "currency_candidate_review",
        "review_layer_version": "1.0",
        "status": "review_records_generated",
        "source": SOURCE,
        "review_group_count": 1,
        "review_groups": [{
            "group_id": "crgrp_example",
            "candidate_type": "currency_amount",
            "normalized_value": {"kind": "currency", "value": 5000, "unit": "INR"},
            "inferred_scope": {"benefit_scope_key": "scope_unresolved", "band_scope_key": "band_unresolved"},
            "review_flags": ["role_selection_required"],
            "supporting_candidates": [{"candidate_id": "excand_example"}],
        }],
    }
    document = ReviewerDecisionRecordContract.build_pending_document(review)
    pending = document["decision_records"][0]
    document["decision_records"][0] = ReviewerDecisionRecordContract.build_resolved_record(
        pending,
        decision="accept",
        reviewer_identity="reviewer@example.test",
        reviewed_at="2026-07-05T12:00:00+05:30",
        review_rationale="Accepted in error.",
        selected_role="sub_limit_or_limit",
        selected_benefit_scope="example_scope",
    )
    document["status"] = "ready_for_submission"
    return document


def test_amends_resolved_record_without_changing_snapshot_or_input():
    source = completed_document()
    before = copy.deepcopy(source)
    record_id = source["decision_records"][0]["decision_record_id"]
    result = ReviewerDecisionAmendmentWorkflow.amend_resolved_record(
        source,
        decision_record_id=record_id,
        decision="reject",
        reviewer_identity="reviewer@example.test",
        reviewed_at="2026-07-05T12:15:00+05:30",
        review_rationale="Duplicate evidence window.",
    )
    assert source == before
    amended = result["decision_records"][0]
    assert amended["decision"] == "reject"
    assert amended["selected_role"] is None
    assert amended["selected_benefit_scope"] is None
    assert amended["review_group_snapshot"] == before["decision_records"][0]["review_group_snapshot"]
    assert result["status"] == "ready_for_submission"
    assert len(result["decision_amendment_history"]) == 1
    assert result["decision_amendment_history"][0]["prior_decision"] == "accept"


def test_rejects_amendment_of_non_completed_document():
    source = completed_document()
    source["status"] = "in_progress_human_review"
    with pytest.raises(ReviewerDecisionAmendmentError, match="ready_for_submission"):
        ReviewerDecisionAmendmentWorkflow.amend_resolved_record(
            source,
            decision_record_id=source["decision_records"][0]["decision_record_id"],
            decision="reject",
            reviewer_identity="reviewer@example.test",
            reviewed_at="2026-07-05T12:15:00+05:30",
            review_rationale="Duplicate evidence window.",
        )
