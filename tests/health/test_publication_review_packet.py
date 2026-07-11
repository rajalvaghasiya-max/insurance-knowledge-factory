from __future__ import annotations

import pytest

from knowledge_domains.health.extraction_primitives.publication_review_packet import (
    PublicationReviewPacketContract,
    PublicationReviewPacketError,
)

SHA = "a" * 64
SOURCE = {"entity_id": "insurer:product", "sha256": SHA, "document_type": "policy_wording"}


def artifacts():
    fact = {
        "canonical_fact_id": "cfact_1",
        "governed_fact_id": "gfact_1",
        "entity_id": "insurer:product",
        "canonical_field_key": "currency_sub_limit",
        "normalized_value": {"kind": "currency", "value": 500, "unit": "INR"},
        "benefit_scope": "daily_cash",
        "applicability": {"sum_insured_band_scope": None},
        "source_document": dict(SOURCE),
        "review_lineage": {"source_decision_record_id": "rdec_1", "source_immutable_record_id": "rsubrec_1"},
    }
    materialization = {
        "materialization_document_type": "health_canonical_fact_materialization_document_v1",
        "status": "materialized_not_published",
        "materialization_id": "fmat_1",
        "source": dict(SOURCE),
        "input": {"source_submission_id": "rsub_1"},
        "canonical_fact_count": 1,
        "canonical_facts": [fact],
    }
    eligibility = {
        "eligibility_document_type": "health_fact_publication_eligibility_document_v1",
        "status": "publication_eligibility_assessed_not_published",
        "eligibility_assessment_id": "felig_1",
        "source": dict(SOURCE),
        "input": {"materialization_id": "fmat_1"},
        "eligibility_records": [{
            "record_kind": "canonical_fact", "canonical_fact_id": "cfact_1", "eligibility_record_id": "feligrec_1",
            "eligibility_status": "eligible_for_publication_review", "eligibility_reason": "passed", "validation_checks": {"source_lineage": "passed"},
        }],
    }
    group = {
        "group_id": "crgrp_1", "normalized_value": {"kind": "currency", "value": 500, "unit": "INR"},
        "bounded_evidence_identity": "evidence_1", "supporting_pages": [2],
        "bounded_evidence": [{"candidate_id": "excand_1", "evidence": {"text": "Daily cash benefit INR 500", "page_number": 2}}],
    }
    submission = {
        "submission_document_type": "health_reviewer_decision_submission_document_v1", "status": "submitted_human_review",
        "submission_id": "rsub_1", "source": dict(SOURCE),
        "submitted_records": [{
            "decision_record_id": "rdec_1", "decision": "accept", "source_sha256": SHA,
            "immutable_record_id": "rsubrec_1", "review_group_id": "crgrp_1", "reviewer_identity": "reviewer",
            "reviewed_at": "2026-07-01T00:00:00+00:00", "review_rationale": "Reviewed.", "review_snapshot_fingerprint": "f" * 64,
            "review_group_snapshot": {"group_id": "crgrp_1", "normalized_value": dict(group["normalized_value"]), "bounded_evidence_identity": "evidence_1"},
        }],
    }
    candidate_review = {
        "review_type": "health_currency_candidate_review_document_v1", "review_layer": "currency_candidate_review",
        "status": "review_records_generated", "source": dict(SOURCE), "review_groups": [group],
    }
    return materialization, eligibility, submission, candidate_review


def build():
    return PublicationReviewPacketContract.build_packet(
        materialization_document=artifacts()[0], eligibility_document=artifacts()[1],
        reviewer_submission_document=artifacts()[2], candidate_review_document=artifacts()[3],
        prepared_by="reviewer", prepared_at="2026-07-02T00:00:00+00:00",
    )


def test_packet_binds_all_immutable_review_sources():
    packet = build()
    assert packet["packet_item_count"] == 1
    item = packet["packet_items"][0]
    assert item["review_status"] == "awaiting_publication_review"
    assert item["bounded_evidence"]["evidence_items"][0]["evidence"]["page_number"] == 2
    assert packet["publication_state"] == "not_published"
    assert packet["reusable_knowledge_state"] == "not_created"


def test_packet_rejects_missing_candidate_review_group():
    materialization, eligibility, submission, candidate_review = artifacts()
    candidate_review["review_groups"] = []
    with pytest.raises(PublicationReviewPacketError, match="candidate review requires review_groups"):
        PublicationReviewPacketContract.build_packet(
            materialization_document=materialization, eligibility_document=eligibility,
            reviewer_submission_document=submission, candidate_review_document=candidate_review,
            prepared_by="reviewer", prepared_at="2026-07-02T00:00:00+00:00",
        )


def test_packet_rejects_non_eligible_canonical_record():
    materialization, eligibility, submission, candidate_review = artifacts()
    eligibility["eligibility_records"][0]["eligibility_status"] = "blocked"
    with pytest.raises(PublicationReviewPacketError, match="exactly match materialized"):
        PublicationReviewPacketContract.build_packet(
            materialization_document=materialization, eligibility_document=eligibility,
            reviewer_submission_document=submission, candidate_review_document=candidate_review,
            prepared_by="reviewer", prepared_at="2026-07-02T00:00:00+00:00",
        )

