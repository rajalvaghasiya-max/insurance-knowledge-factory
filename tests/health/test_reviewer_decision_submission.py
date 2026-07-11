from __future__ import annotations

import copy

import pytest

from knowledge_domains.health.extraction_primitives.reviewer_decision_record import ReviewerDecisionRecordContract
from knowledge_domains.health.extraction_primitives.reviewer_decision_submission import (
    ReviewerDecisionSubmissionContract,
    ReviewerDecisionSubmissionError,
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


def review_document():
    return {
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
            "normalized_value": {"kind": "currency", "value": 50000, "unit": "INR"},
            "inferred_scope": {"benefit_scope_key": "maternity", "band_scope_key": "for_si_5_lac_to_10_lac"},
            "review_flags": ["role_selection_required"],
            "supporting_candidates": [{"candidate_id": "excand_example"}],
        }],
    }


def completed_document():
    pending = ReviewerDecisionRecordContract.build_pending_document(review_document())
    pending["decision_records"][0] = ReviewerDecisionRecordContract.build_resolved_record(
        pending["decision_records"][0],
        decision="accept",
        reviewer_identity="reviewer@example.test",
        reviewed_at="2026-07-05T12:00:00Z",
        review_rationale="Reviewed the bounded clause and source-linked evidence.",
        selected_role="sub_limit_or_limit",
        selected_benefit_scope="maternity",
        selected_band_scope="for_si_5_lac_to_10_lac",
    )
    pending["status"] = "completed_human_review"
    return pending


def test_builds_immutable_submission_without_fact_promotion():
    result = ReviewerDecisionSubmissionContract.build_submission_document(
        completed_document(), submitted_by="reviewer@example.test", submitted_at="2026-07-05T12:30:00Z"
    )
    assert result["status"] == "submitted_human_review"
    assert result["submitted_record_count"] == 1
    record = result["submitted_records"][0]
    assert record["revision"] == 1
    assert record["supersedes_immutable_record_id"] is None
    assert record["non_fact_guardrail"] == "submitted_review_only_no_canonical_fact"


def test_rejects_submission_with_pending_record():
    pending = ReviewerDecisionRecordContract.build_pending_document(review_document())
    with pytest.raises(ReviewerDecisionSubmissionError, match="all decision records must be resolved"):
        ReviewerDecisionSubmissionContract.build_submission_document(
            pending, submitted_by="reviewer@example.test", submitted_at="2026-07-05T12:30:00Z"
        )


def test_submission_rejects_changed_source_hash():
    completed = completed_document()
    completed["decision_records"][0]["source_sha256"] = "b" * 64
    with pytest.raises(ReviewerDecisionSubmissionError, match="match document source"):
        ReviewerDecisionSubmissionContract.build_submission_document(
            completed, submitted_by="reviewer@example.test", submitted_at="2026-07-05T12:30:00Z"
        )


def test_revision_links_to_previous_immutable_record():
    first = ReviewerDecisionSubmissionContract.build_submission_document(
        completed_document(), submitted_by="reviewer@example.test", submitted_at="2026-07-05T12:30:00Z"
    )
    second_completed = completed_document()
    second_completed["decision_records"][0]["review_rationale"] = "Corrected rationale after a second bounded review."
    second = ReviewerDecisionSubmissionContract.build_submission_document(
        second_completed,
        submitted_by="reviewer@example.test",
        submitted_at="2026-07-05T13:00:00Z",
        previous_submission_document=first,
    )
    record = second["submitted_records"][0]
    assert record["revision"] == 2
    assert record["supersedes_immutable_record_id"] == first["submitted_records"][0]["immutable_record_id"]


def test_revision_rejects_changed_snapshot():
    first = ReviewerDecisionSubmissionContract.build_submission_document(
        completed_document(), submitted_by="reviewer@example.test", submitted_at="2026-07-05T12:30:00Z"
    )
    changed = completed_document()
    changed["decision_records"][0]["review_group_snapshot"]["normalized_value"]["value"] = 75000
    with pytest.raises(ReviewerDecisionSubmissionError, match="snapshot"):
        ReviewerDecisionSubmissionContract.build_submission_document(
            changed,
            submitted_by="reviewer@example.test",
            submitted_at="2026-07-05T13:00:00Z",
            previous_submission_document=first,
        )
