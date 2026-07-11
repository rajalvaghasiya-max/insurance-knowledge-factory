from __future__ import annotations

import copy

import pytest

from knowledge_domains.health.extraction_primitives.canonical_fact_materialization import (
    CanonicalFactMaterializationContract,
    CanonicalFactMaterializationError,
)
from knowledge_domains.health.extraction_primitives.governed_fact_selection import (
    GovernedFactSelectionContract,
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


def _review_group(group_id: str, value: int, benefit_scope: str = "example_benefit", band_scope: str | None = None):
    return {
        "group_id": group_id,
        "candidate_type": "currency_amount",
        "normalized_value": {"kind": "currency", "value": value, "unit": "INR"},
        "inferred_scope": {"benefit_scope_key": benefit_scope, "band_scope_key": band_scope},
        "review_flags": ["role_selection_required"],
        "supporting_candidates": [{"candidate_id": "excand_" + group_id}],
    }


def _selection(*, groups: list[dict] | None = None, role: str = "sub_limit_or_limit"):
    groups = groups or [_review_group("crgrp_example", 50000)]
    review = {
        "schema_version": "1.0",
        "review_type": "health_currency_candidate_review_document_v1",
        "review_layer": "currency_candidate_review",
        "review_layer_version": "1.0",
        "status": "review_records_generated",
        "source": SOURCE,
        "review_group_count": len(groups),
        "review_groups": groups,
    }
    pending = ReviewerDecisionRecordContract.build_pending_document(review)
    for index, record in enumerate(pending["decision_records"]):
        scope = groups[index]["inferred_scope"]
        pending["decision_records"][index] = ReviewerDecisionRecordContract.build_resolved_record(
            record,
            decision="accept",
            reviewer_identity="reviewer@example.test",
            reviewed_at="2026-07-05T12:00:00Z",
            review_rationale="Reviewed the bounded clause and source-linked evidence.",
            selected_role=role,
            selected_benefit_scope=scope["benefit_scope_key"],
            selected_band_scope=scope["band_scope_key"],
        )
    pending["status"] = "completed_human_review"
    submission = ReviewerDecisionSubmissionContract.build_submission_document(
        pending, submitted_by="submitter@example.test", submitted_at="2026-07-05T12:30:00Z"
    )
    return GovernedFactSelectionContract.build_selection_document(
        submission, selector_identity="selector@example.test", selected_at="2026-07-05T13:00:00Z"
    )


def test_materializes_selected_currency_sub_limit_without_publication():
    result = CanonicalFactMaterializationContract.build_materialization_document(
        _selection(), materialized_by="materializer@example.test", materialized_at="2026-07-05T13:30:00Z"
    )
    fact = result["canonical_facts"][0]
    assert result["status"] == "materialized_not_published"
    assert result["canonical_fact_count"] == 1
    assert fact["canonical_field_key"] == "currency_sub_limit"
    assert fact["canonical_fact_id"].startswith("cfact_")
    assert fact["publication_state"] == "not_published"
    assert fact["entitlement_state"] == "not_evaluated"


def test_rejects_selection_with_no_selected_records():
    with pytest.raises(CanonicalFactMaterializationError, match="no selected_governed_fact"):
        CanonicalFactMaterializationContract.build_materialization_document(
            _selection(role="premium"), materialized_by="materializer@example.test", materialized_at="2026-07-05T13:30:00Z"
        )


def test_accounts_for_deferred_record_alongside_selected_fact():
    selection = _selection()
    deferred = copy.deepcopy(selection["selection_records"][0])
    deferred["selection_record_id"] = "fsel_deferredexample"
    deferred["selection_status"] = "deferred"
    deferred["canonical_field_key"] = None
    deferred["governed_fact_id"] = None
    deferred["selection_reason"] = "outside the field registry"
    selection["selection_records"].append(deferred)
    selection["selection_record_count"] = 2
    result = CanonicalFactMaterializationContract.build_materialization_document(
        selection, materialized_by="materializer@example.test", materialized_at="2026-07-05T13:30:00Z"
    )
    assert result["canonical_fact_count"] == 1
    assert result["non_materialized_selection_record_count"] == 1
    assert result["non_materialized_selection_records"][0]["selection_status"] == "deferred"


def test_rejects_duplicate_field_benefit_band_key():
    selection = _selection(groups=[_review_group("one", 50000), _review_group("two", 60000)])
    with pytest.raises(CanonicalFactMaterializationError, match="duplicate canonical fact key"):
        CanonicalFactMaterializationContract.build_materialization_document(
            selection, materialized_by="materializer@example.test", materialized_at="2026-07-05T13:30:00Z"
        )


def test_rejects_tampered_source_sha_lineage():
    selection = _selection()
    selection["selection_records"][0]["source_sha256"] = "b" * 64
    with pytest.raises(CanonicalFactMaterializationError, match="source_sha256"):
        CanonicalFactMaterializationContract.build_materialization_document(
            selection, materialized_by="materializer@example.test", materialized_at="2026-07-05T13:30:00Z"
        )


def test_rejects_tampered_materialized_fact_that_claims_publication():
    result = CanonicalFactMaterializationContract.build_materialization_document(
        _selection(), materialized_by="materializer@example.test", materialized_at="2026-07-05T13:30:00Z"
    )
    tampered = copy.deepcopy(result)
    tampered["canonical_facts"][0]["publication_state"] = "published"
    with pytest.raises(CanonicalFactMaterializationError, match="not_published"):
        CanonicalFactMaterializationContract.validate_materialization_document(tampered)



def test_non_materialized_record_preserves_reviewed_selection_semantics():
    selection = _selection()
    deferred = copy.deepcopy(selection["selection_records"][0])
    deferred["selection_record_id"] = "fsel_deferredexample"
    deferred["selection_status"] = "deferred"
    deferred["canonical_field_key"] = None
    deferred["governed_fact_id"] = None
    deferred["normalized_value"] = {"kind": "currency", "value": 2500, "unit": "INR"}
    deferred["selected_role"] = "premium"
    deferred["selected_benefit_scope"] = "minimum_premium"
    deferred["selected_band_scope"] = None
    deferred["selection_reason"] = "outside field registry"
    selection["selection_records"].append(deferred)
    selection["selection_record_count"] = 2

    materialization = CanonicalFactMaterializationContract.build_materialization_document(
        selection, materialized_by="materializer@example.test", materialized_at="2026-07-05T13:30:00Z"
    )
    record = materialization["non_materialized_selection_records"][0]
    assert record["normalized_value"] == {"kind": "currency", "value": 2500, "unit": "INR"}
    assert record["selected_role"] == "premium"
    assert record["selected_benefit_scope"] == "minimum_premium"
    assert record["selected_band_scope"] is None
