
from __future__ import annotations

import copy

import pytest

from knowledge_domains.health.extraction_primitives.publication_review_decision_submission import (
    PublicationReviewDecisionSubmissionContract,
    PublicationReviewDecisionSubmissionError,
)


def packet() -> dict:
    return {
        "schema_version": "1.0",
        "status": "publication_review_packet_prepared_pending_human_review",
        "publication_review_packet_id": "prpkt_example",
        "packet_items": [
            {
                "packet_item_id": "prpktitem_one",
                "review_status": "awaiting_publication_review",
                "canonical_fact": {
                    "canonical_fact_id": "cfact_one",
                    "governed_fact_id": "gfact_one",
                },
                "publication_eligibility": {
                    "eligibility_record_id": "feligrec_one",
                    "eligibility_status": "eligible_for_publication_review",
                },
                "review_lineage": {
                    "source_submission_id": "rsub_one",
                    "source_immutable_record_id": "rsubrec_one",
                    "source_decision_record_id": "rdec_one",
                    "review_group_id": "crgrp_one",
                },
            },
            {
                "packet_item_id": "prpktitem_two",
                "review_status": "awaiting_publication_review",
                "canonical_fact": {
                    "canonical_fact_id": "cfact_two",
                    "governed_fact_id": "gfact_two",
                },
                "publication_eligibility": {
                    "eligibility_record_id": "feligrec_two",
                    "eligibility_status": "eligible_for_publication_review",
                },
                "review_lineage": {
                    "source_submission_id": "rsub_two",
                    "source_immutable_record_id": "rsubrec_two",
                    "source_decision_record_id": "rdec_two",
                    "review_group_id": "crgrp_two",
                },
            },
        ],
    }


def decision_spec(source_packet: dict) -> dict:
    template = PublicationReviewDecisionSubmissionContract.build_template(
        packet_document=source_packet,
        prepared_by="reviewer",
        prepared_at="2026-07-07T00:00:00Z",
    )
    template["reviewed_by_human"] = True
    template["reviewer_identity"] = "reviewer"
    template["reviewed_at"] = "2026-07-07T01:00:00Z"
    template["decisions"][0]["decision"] = "approve_for_governed_publication"
    template["decisions"][0]["rationale"] = "Bounded evidence, applicability, and review lineage are sufficient for reusable knowledge drafting."
    template["decisions"][1]["decision"] = "defer"
    template["decisions"][1]["rationale"] = "Need a narrower human interpretation before reusable knowledge drafting."
    return template


def test_records_complete_non_publishing_submission():
    source_packet = packet()
    result = PublicationReviewDecisionSubmissionContract.record(
        packet_document=source_packet,
        decision_spec=decision_spec(source_packet),
    )
    assert result["status"] == "human_publication_review_decisions_recorded_not_published"
    assert result["submitted_decision_count"] == 2
    assert result["decision_counts"]["approve_for_governed_publication"] == 1
    assert result["decision_counts"]["defer"] == 1
    assert all(item["publication_state"] == "not_published" for item in result["submitted_decisions"])
    assert all(item["reusable_knowledge_state"] == "not_created" for item in result["submitted_decisions"])


def test_rejects_incomplete_decision_set():
    source_packet = packet()
    spec = decision_spec(source_packet)
    spec["decisions"] = spec["decisions"][:1]
    with pytest.raises(PublicationReviewDecisionSubmissionError, match="decision count must exactly match"):
        PublicationReviewDecisionSubmissionContract.record(
            packet_document=source_packet,
            decision_spec=spec,
        )


def test_rejects_wrong_packet_binding():
    source_packet = packet()
    spec = decision_spec(source_packet)
    spec["source_publication_review_packet_id"] = "prpkt_other"
    with pytest.raises(PublicationReviewDecisionSubmissionError, match="packet ID does not match"):
        PublicationReviewDecisionSubmissionContract.record(
            packet_document=source_packet,
            decision_spec=spec,
        )
