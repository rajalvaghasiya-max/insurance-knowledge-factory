from __future__ import annotations

import copy

import pytest

from knowledge_domains.health.extraction_primitives.reviewer_decision_record import ReviewerDecisionRecordContract
from knowledge_domains.health.extraction_primitives.reviewer_fill_workflow import (
    ReviewerFillWorkflow,
    ReviewerFillWorkflowError,
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


def pending_document():
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
            "normalized_value": {"kind": "currency", "value": 50000, "unit": "INR"},
            "inferred_scope": {
                "benefit_scope_key": "family_visit",
                "band_scope_key": "for_si_more_than_10_lacs",
                "scope_inference_requires_review": True,
            },
            "review_flags": [
                "role_selection_required",
                "schedule_or_band_binding_unverified",
                "possible_benefit_limit_despite_role_hint",
            ],
            "supporting_candidates": [{"candidate_id": "excand_example"}],
        }],
    }
    return ReviewerDecisionRecordContract.build_pending_document(review)


def test_builds_read_only_worklist_with_scope_sensitive_checklist():
    source = pending_document()
    before = copy.deepcopy(source)
    result = ReviewerFillWorkflow.build_worklist_document(source)
    assert result["status"] == "ready_for_human_review"
    assert result["work_item_count"] == 1
    item = result["work_items"][0]
    assert item["source_sha256"] == SHA
    assert item["non_fact_guardrail"] == "review_worklist_only_no_canonical_fact"
    assert any("layout/table" in step for step in item["reviewer_checklist"])
    assert source == before


def test_worklist_exposes_controlled_decisions_and_accept_requirements():
    result = ReviewerFillWorkflow.build_worklist_document(pending_document())
    assert result["workflow_rules"]["allowed_decisions"] == ["accept", "reject", "split_further", "defer"]
    assert "selected_role" in result["workflow_rules"]["accept_requires"]
    assert "review_rationale" in result["workflow_rules"]["non_accept_requires"]


def test_rejects_completed_or_mixed_decision_document():
    completed = pending_document()
    completed["status"] = "completed_human_review"
    with pytest.raises(ReviewerFillWorkflowError, match="pending_human_review"):
        ReviewerFillWorkflow.build_worklist_document(completed)


def test_validation_rejects_source_mismatch():
    result = ReviewerFillWorkflow.build_worklist_document(pending_document())
    result["work_items"][0]["source_sha256"] = "b" * 64
    with pytest.raises(ReviewerFillWorkflowError, match="match document source"):
        ReviewerFillWorkflow.validate_worklist_document(result)
