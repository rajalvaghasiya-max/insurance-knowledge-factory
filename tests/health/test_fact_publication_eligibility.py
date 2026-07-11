from __future__ import annotations

import copy

import pytest

from knowledge_domains.health.extraction_primitives.canonical_fact_materialization import (
    CanonicalFactMaterializationContract,
)
from knowledge_domains.health.extraction_primitives.fact_publication_eligibility import (
    FactPublicationEligibilityContract,
    FactPublicationEligibilityError,
)
from knowledge_domains.health.extraction_primitives.governed_fact_selection import GovernedFactSelectionContract
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


def _materialization():
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
            "inferred_scope": {"benefit_scope_key": "example_benefit", "band_scope_key": None},
            "review_flags": ["role_selection_required"],
            "supporting_candidates": [{"candidate_id": "excand_example"}],
        }],
    }
    pending = ReviewerDecisionRecordContract.build_pending_document(review)
    pending["decision_records"][0] = ReviewerDecisionRecordContract.build_resolved_record(
        pending["decision_records"][0], decision="accept", reviewer_identity="reviewer@example.test",
        reviewed_at="2026-07-05T12:00:00Z", review_rationale="Verified bounded source.",
        selected_role="sub_limit_or_limit", selected_benefit_scope="example_benefit", selected_band_scope=None,
    )
    pending["status"] = "completed_human_review"
    submission = ReviewerDecisionSubmissionContract.build_submission_document(
        pending, submitted_by="submitter@example.test", submitted_at="2026-07-05T12:30:00Z"
    )
    selection = GovernedFactSelectionContract.build_selection_document(
        submission, selector_identity="selector@example.test", selected_at="2026-07-05T13:00:00Z"
    )
    return CanonicalFactMaterializationContract.build_materialization_document(
        selection, materialized_by="materializer@example.test", materialized_at="2026-07-05T13:30:00Z"
    )


def _overlay(*, temporal="current_observed_reviewed", eligibility="eligible", resolution="resolved"):
    return {
        "schema_version": "1.0",
        "overlay_type": "document_identity_resolution_overlay_v1",
        "overlay_status": "reviewed_document_identity_resolution_recorded_not_published",
        "product_identity_reference": {"entity_id": "example:product"},
        "documents": [{
            "document_version_link": {
                "content_sha256": SHA, "document_type": "policy_wording",
                "document_version_id": "docver_example", "document_id": "example_policy_wording",
            },
            "identity_resolution": {
                "resolution_status": resolution,
                "evidence_review_eligibility": "eligible_for_evidence_review",
                "temporal_status": temporal,
                "current_entitlement_publication_eligibility": eligibility,
            },
        }],
    }


def test_current_reviewed_identity_makes_fact_eligible_for_publication_review():
    result = FactPublicationEligibilityContract.build_eligibility_document(
        _materialization(), _overlay(), validated_by="validator@example.test", validated_at="2026-07-05T14:00:00Z"
    )
    assert result["eligible_for_publication_review_count"] == 1
    assert result["blocked_count"] == 0
    assert result["eligibility_records"][0]["eligibility_status"] == "eligible_for_publication_review"
    assert result["publication_state"] == "not_published"


def test_compatibility_unverified_blocks_materialized_fact():
    result = FactPublicationEligibilityContract.build_eligibility_document(
        _materialization(), _overlay(temporal="compatibility_unverified", eligibility="blocked"),
        validated_by="validator@example.test", validated_at="2026-07-05T14:00:00Z"
    )
    assert result["eligible_for_publication_review_count"] == 0
    assert result["blocked_count"] == 1
    assert result["eligibility_records"][0]["eligibility_reason"] == "currentness_not_eligible:compatibility_unverified"


def test_rejects_overlay_entity_mismatch():
    overlay = _overlay()
    overlay["product_identity_reference"]["entity_id"] = "other:product"
    with pytest.raises(FactPublicationEligibilityError, match="entity_id"):
        FactPublicationEligibilityContract.build_eligibility_document(
            _materialization(), overlay, validated_by="validator@example.test", validated_at="2026-07-05T14:00:00Z"
        )


def test_rejects_overlay_without_matching_hash():
    overlay = _overlay()
    overlay["documents"][0]["document_version_link"]["content_sha256"] = "b" * 64
    with pytest.raises(FactPublicationEligibilityError, match="exactly one matching"):
        FactPublicationEligibilityContract.build_eligibility_document(
            _materialization(), overlay, validated_by="validator@example.test", validated_at="2026-07-05T14:00:00Z"
        )


def test_rejects_duplicate_applicability_key_in_tampered_materialization():
    materialization = _materialization()
    duplicate = copy.deepcopy(materialization["canonical_facts"][0])
    duplicate["canonical_fact_id"] = "cfact_duplicateexample"
    materialization["canonical_facts"].append(duplicate)
    materialization["canonical_fact_count"] = 2
    with pytest.raises(FactPublicationEligibilityError, match="duplicate canonical fact key"):
        FactPublicationEligibilityContract.build_eligibility_document(
            materialization, _overlay(), validated_by="validator@example.test", validated_at="2026-07-05T14:00:00Z"
        )


def test_rejects_tampered_eligibility_document_that_claims_publication():
    result = FactPublicationEligibilityContract.build_eligibility_document(
        _materialization(), _overlay(), validated_by="validator@example.test", validated_at="2026-07-05T14:00:00Z"
    )
    result["eligibility_records"][0]["publication_state"] = "published"
    with pytest.raises(FactPublicationEligibilityError, match="not_published"):
        FactPublicationEligibilityContract.validate_eligibility_document(result)


def test_non_materialized_input_remains_deferred():
    materialization = _materialization()
    base = {
        "selection_record_id": "fsel_deferredexample",
        "source_submission_id": materialization["input"]["source_submission_id"],
        "source_sha256": SHA,
        "selection_status": "deferred",
        "normalized_value": {"kind": "currency", "value": 2500, "unit": "INR"},
        "selected_role": "premium",
        "selected_benefit_scope": "minimum_premium",
        "selected_band_scope": None,
        "non_materialization_reason": "outside field registry",
        "publication_state": "not_published",
        "entitlement_state": "not_evaluated",
    }
    materialization["non_materialized_selection_records"] = [base]
    materialization["non_materialized_selection_record_count"] = 1
    materialization["input"]["selection_record_count"] = 2
    result = FactPublicationEligibilityContract.build_eligibility_document(
        materialization, _overlay(), validated_by="validator@example.test", validated_at="2026-07-05T14:00:00Z"
    )
    assert result["deferred_count"] == 1
    deferred_output = result["eligibility_records"][1]
    assert deferred_output["eligibility_status"] == "deferred"
    assert deferred_output["normalized_value"] == {"kind": "currency", "value": 2500, "unit": "INR"}
    assert deferred_output["selected_role"] == "premium"
    assert deferred_output["selected_benefit_scope"] == "minimum_premium"
    assert deferred_output["selected_band_scope"] is None
