from __future__ import annotations

import copy

import pytest

from knowledge_domains.health.extraction_primitives.reviewer_decision_fill import (
    ReviewerDecisionFillError,
    ReviewerDecisionFillWorkflow,
)
from knowledge_domains.health.extraction_primitives.reviewer_decision_record import (
    ReviewerDecisionRecordContract,
)

SHA = "a" * 64


def _pending_document() -> dict:
    source = {"sha256": SHA}
    review_document = {
        "review_type": "health_currency_candidate_review_document_v1",
        "status": "review_records_generated",
        "source": source,
        "review_group_count": 2,
        "review_groups": [
            {
                "group_id": "group_general",
                "candidate_type": "currency_amount",
                "normalized_value": {"kind": "currency", "value": 500, "unit": "INR"},
                "inferred_scope": {"benefit_scope_key": "general_physician_consultation", "band_scope_key": "band_unresolved"},
                "review_flags": ["role_selection_required"],
                "supporting_candidates": [{"candidate_id": "candidate_general"}],
            },
            {
                "group_id": "group_family",
                "candidate_type": "currency_amount",
                "normalized_value": {"kind": "currency", "value": 25000, "unit": "INR"},
                "inferred_scope": {"benefit_scope_key": "family_visit", "band_scope_key": "for_si_upto_10_lacs"},
                "review_flags": ["schedule_or_band_binding_unverified"],
                "supporting_candidates": [{"candidate_id": "candidate_family"}],
            },
        ],
        "review_layer": "currency_candidate_review",
        "review_layer_version": "1.0",
    }
    return ReviewerDecisionRecordContract.build_pending_document(review_document)


def _fill(document: dict, **overrides) -> dict:
    args = {
        "decision_record_id": document["decision_records"][0]["decision_record_id"],
        "decision": "accept",
        "reviewer_identity": "reviewer@example.test",
        "reviewed_at": "2026-07-05T15:30:00+05:30",
        "review_rationale": "Verified bounded source wording and selected benefit scope.",
        "selected_role": "sub_limit_or_limit",
        "selected_benefit_scope": "general_physician_consultation",
        "selected_band_scope": None,
    }
    args.update(overrides)
    return ReviewerDecisionFillWorkflow.fill_pending_record(document, **args)


def test_fill_resolves_one_record_without_mutating_input():
    original = _pending_document()
    original_copy = copy.deepcopy(original)
    result = _fill(original)

    assert original == original_copy
    assert result["status"] == "in_progress_human_review"
    assert result["decision_records"][0]["review_status"] == "decision_recorded"
    assert result["decision_records"][0]["decision"] == "accept"
    assert result["decision_records"][0]["selected_role"] == "sub_limit_or_limit"
    assert result["decision_records"][1] == original["decision_records"][1]
    ReviewerDecisionRecordContract.validate_decision_document(result)


def test_non_accept_clears_scope_fields_requirement():
    document = _pending_document()
    result = _fill(
        document,
        decision="defer",
        selected_role=None,
        selected_benefit_scope=None,
        review_rationale="Original layout is required before resolving the band binding.",
    )
    assert result["decision_records"][0]["decision"] == "defer"
    assert result["decision_records"][0]["selected_role"] is None


def test_accept_requires_controlled_role_and_scope():
    document = _pending_document()
    with pytest.raises(ReviewerDecisionFillError, match="selected_role"):
        _fill(document, selected_role="invented_role")
    with pytest.raises(ReviewerDecisionFillError, match="selected_benefit_scope"):
        _fill(document, selected_benefit_scope="")


def test_non_accept_rejects_selected_fields():
    document = _pending_document()
    with pytest.raises(ReviewerDecisionFillError, match="must not set selected role or scope"):
        _fill(
            document,
            decision="reject",
            selected_role="premium",
            selected_benefit_scope="minimum_premium",
        )


def test_resolved_record_cannot_be_refilled_and_all_resolved_is_ready_for_submission():
    document = _pending_document()
    first = _fill(document)
    with pytest.raises(ReviewerDecisionFillError, match="only pending_review"):
        _fill(first)
    second_id = first["decision_records"][1]["decision_record_id"]
    completed = _fill(
        first,
        decision_record_id=second_id,
        decision="defer",
        selected_role=None,
        selected_benefit_scope=None,
        review_rationale="Awaiting original schedule layout review.",
    )
    assert completed["status"] == "ready_for_submission"
