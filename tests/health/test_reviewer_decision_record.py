from __future__ import annotations

import copy

import pytest

from knowledge_domains.health.extraction_primitives.reviewer_decision_record import (
    ReviewerDecisionRecordContract,
    ReviewerDecisionRecordError,
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


def test_builds_source_bound_pending_records_without_fact_promotion():
    result = ReviewerDecisionRecordContract.build_pending_document(review_document())
    assert result["decision_document_type"] == "health_reviewer_decision_document_v1"
    assert result["status"] == "pending_human_review"
    assert result["decision_record_count"] == 1
    record = result["decision_records"][0]
    assert record["review_status"] == "pending_review"
    assert record["source_sha256"] == SHA
    assert record["decision"] is None
    assert record["non_fact_guardrail"] == "review_decision_only_no_canonical_fact"


def test_pending_record_rejects_premature_decision_fields():
    result = ReviewerDecisionRecordContract.build_pending_document(review_document())
    result["decision_records"][0]["decision"] = "accept"
    with pytest.raises(ReviewerDecisionRecordError, match="pending review record"):
        ReviewerDecisionRecordContract.validate_decision_document(result)


def test_accept_requires_role_scope_rationale_reviewer_and_timestamp():
    pending = ReviewerDecisionRecordContract.build_pending_document(review_document())["decision_records"][0]
    with pytest.raises(ReviewerDecisionRecordError, match="selected_role"):
        ReviewerDecisionRecordContract.build_resolved_record(
            pending,
            decision="accept",
            reviewer_identity="reviewer@example.test",
            reviewed_at="2026-07-05T12:00:00Z",
            review_rationale="Reviewed clause and confirmed the interpretation.",
        )


def test_accept_is_valid_decision_record_but_not_a_fact():
    pending = ReviewerDecisionRecordContract.build_pending_document(review_document())["decision_records"][0]
    resolved = ReviewerDecisionRecordContract.build_resolved_record(
        pending,
        decision="accept",
        reviewer_identity="reviewer@example.test",
        reviewed_at="2026-07-05T12:00:00Z",
        review_rationale="Reviewed the policy wording and selected the bounded clause meaning.",
        selected_role="sub_limit_or_limit",
        selected_benefit_scope="maternity",
        selected_band_scope="for_si_5_lac_to_10_lac",
    )
    assert resolved["review_status"] == "decision_recorded"
    assert resolved["non_fact_guardrail"] == "review_decision_only_no_canonical_fact"


def test_rejects_decision_record_when_source_hash_changes():
    result = ReviewerDecisionRecordContract.build_pending_document(review_document())
    bad = copy.deepcopy(result)
    bad["decision_records"][0]["source_sha256"] = "b" * 64
    with pytest.raises(ReviewerDecisionRecordError, match="match document source"):
        ReviewerDecisionRecordContract.validate_decision_document(bad)
