from __future__ import annotations

from knowledge_domains.health.extraction_primitives.canonical_fact_materialization import CanonicalFactMaterializationContract
from knowledge_domains.health.extraction_primitives.governed_fact_selection import GovernedFactSelectionContract
from knowledge_domains.health.extraction_primitives.reviewer_decision_record import ReviewerDecisionRecordContract
from knowledge_domains.health.extraction_primitives.reviewer_decision_submission import ReviewerDecisionSubmissionContract

SHA = "a" * 64
SOURCE = {"entity_id":"example:product","insurer_id":"example","document_type":"policy_wording","source_document_id":"sha256:"+SHA,"sha256":SHA,"source_url":"https://example.test/policy.pdf","source_page_url":"https://example.test/product","relative_archive_path":"archive/raw_pdf/example/policy.pdf","provenance_status":"download_registry_verified"}

def selection(role: str, band: str | None = None):
    review = {"schema_version":"1.0","review_type":"health_currency_candidate_review_document_v1","review_layer":"currency_candidate_review","review_layer_version":"1.0","status":"review_records_generated","source":SOURCE,"review_group_count":1,"review_groups":[{"group_id":"crgrp_example","candidate_type":"currency_amount","normalized_value":{"kind":"currency","value":50000,"unit":"INR"},"inferred_scope":{"benefit_scope_key":"example_scope","band_scope_key":band},"review_flags":["role_selection_required"],"supporting_candidates":[{"candidate_id":"excand_example"}]}]}
    pending = ReviewerDecisionRecordContract.build_pending_document(review)
    pending["decision_records"][0] = ReviewerDecisionRecordContract.build_resolved_record(
        pending["decision_records"][0], decision="accept", reviewer_identity="reviewer@example.test",
        reviewed_at="2026-07-06T12:00:00Z", review_rationale="Reviewed bounded evidence.",
        selected_role=role, selected_benefit_scope="example_scope", selected_band_scope=band)
    pending["status"] = "completed_human_review"
    submission = ReviewerDecisionSubmissionContract.build_submission_document(pending, submitted_by="submitter@example.test", submitted_at="2026-07-06T12:30:00Z")
    return GovernedFactSelectionContract.build_selection_document(submission, selector_identity="selector@example.test", selected_at="2026-07-06T13:00:00Z")

def test_selects_deductible_from_registry():
    assert selection("deductible")["selection_records"][0]["canonical_field_key"] == "currency_deductible_option"

def test_selects_threshold_with_band():
    assert selection("sum_insured", "base_sum_insured_inr_300000_and_above")["selection_records"][0]["canonical_field_key"] == "currency_sum_insured_threshold"

def test_blocks_threshold_without_band():
    row = selection("sum_insured")["selection_records"][0]
    assert row["selection_status"] == "blocked"
    assert "selected_band_scope" in row["selection_reason"]

def test_materializes_registry_selected_deductible():
    output = CanonicalFactMaterializationContract.build_materialization_document(selection("deductible"), materialized_by="materializer@example.test", materialized_at="2026-07-06T13:30:00Z")
    assert output["canonical_facts"][0]["canonical_field_key"] == "currency_deductible_option"
    assert output["canonical_facts"][0]["publication_state"] == "not_published"
