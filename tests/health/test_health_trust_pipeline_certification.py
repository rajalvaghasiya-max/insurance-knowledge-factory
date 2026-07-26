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
from knowledge_domains.health.extraction_primitives.governed_fact_selection import (
    GovernedFactSelectionContract,
)
from knowledge_domains.health.extraction_primitives.governed_product_knowledge_content_review import (
    APPROVE_DECISION,
    GovernedProductKnowledgeContentReviewContract,
    GovernedProductKnowledgeContentReviewError,
)
from knowledge_domains.health.extraction_primitives.governed_product_knowledge_package import (
    GovernedProductKnowledgePackageContract,
    GovernedProductKnowledgePackageError,
)
from knowledge_domains.health.extraction_primitives.governed_reusable_product_knowledge_records import (
    GovernedReusableProductKnowledgeRecordContract,
    GovernedReusableProductKnowledgeRecordError,
)
from knowledge_domains.health.extraction_primitives.publication_review_decision_submission import (
    PublicationReviewDecisionSubmissionContract,
)
from knowledge_domains.health.extraction_primitives.publication_review_packet import (
    PublicationReviewPacketContract,
)
from knowledge_domains.health.extraction_primitives.reviewer_decision_record import (
    ReviewerDecisionRecordContract,
)
from knowledge_domains.health.extraction_primitives.reviewer_decision_submission import (
    ReviewerDecisionSubmissionContract,
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


def _candidate_review_document() -> dict:
    return {
        "schema_version": "1.0",
        "review_type": "health_currency_candidate_review_document_v1",
        "review_layer": "currency_candidate_review",
        "review_layer_version": "1.0",
        "status": "review_records_generated",
        "source": SOURCE,
        "review_group_count": 1,
        "review_groups": [
            {
                "group_id": "crgrp_example",
                "candidate_type": "currency_amount",
                "normalized_value": {"kind": "currency", "value": 50000, "unit": "INR"},
                "inferred_scope": {
                    "benefit_scope_key": "example_benefit",
                    "band_scope_key": None,
                },
                "review_flags": ["role_selection_required"],
                "supporting_candidates": [{"candidate_id": "excand_example"}],
                "bounded_evidence_identity": "evidence_1",
                "supporting_pages": [2],
                "bounded_evidence": [
                    {
                        "candidate_id": "excand_example",
                        "evidence": {
                            "text": "Example benefit has INR 50,000 limit.",
                            "page_number": 2,
                        },
                    }
                ],
            }
        ],
    }


def _reviewer_submission_document(*, decision: str = "accept") -> dict:
    pending = ReviewerDecisionRecordContract.build_pending_document(
        _candidate_review_document()
    )

    pending["decision_records"][0] = ReviewerDecisionRecordContract.build_resolved_record(
        pending["decision_records"][0],
        decision=decision,
        reviewer_identity="reviewer@example.test",
        reviewed_at="2026-07-05T12:00:00Z",
        review_rationale="Verified bounded source.",
        selected_role="sub_limit_or_limit",
        selected_benefit_scope="example_benefit",
        selected_band_scope=None,
    )
    pending["status"] = "completed_human_review"

    return ReviewerDecisionSubmissionContract.build_submission_document(
        pending,
        submitted_by="submitter@example.test",
        submitted_at="2026-07-05T12:30:00Z",
    )


def _selection_document(*, reviewer_decision: str = "accept") -> dict:
    return GovernedFactSelectionContract.build_selection_document(
        _reviewer_submission_document(decision=reviewer_decision),
        selector_identity="selector@example.test",
        selected_at="2026-07-05T13:00:00Z",
    )


def _materialization_document() -> dict:
    return CanonicalFactMaterializationContract.build_materialization_document(
        _selection_document(),
        materialized_by="materializer@example.test",
        materialized_at="2026-07-05T13:30:00Z",
    )


def _identity_overlay() -> dict:
    return {
        "schema_version": "1.0",
        "overlay_type": "document_identity_resolution_overlay_v1",
        "overlay_status": "reviewed_document_identity_resolution_recorded_not_published",
        "product_identity_reference": {"entity_id": "example:product"},
        "documents": [
            {
                "document_version_link": {
                    "content_sha256": SHA,
                    "document_type": "policy_wording",
                    "document_version_id": "docver_example",
                    "document_id": "example_policy_wording",
                },
                "identity_resolution": {
                    "resolution_status": "resolved",
                    "evidence_review_eligibility": "eligible_for_evidence_review",
                    "temporal_status": "current_observed_reviewed",
                    "current_entitlement_publication_eligibility": "eligible",
                },
            }
        ],
    }


def _eligibility_document() -> dict:
    return FactPublicationEligibilityContract.build_eligibility_document(
        _materialization_document(),
        _identity_overlay(),
        validated_by="validator@example.test",
        validated_at="2026-07-05T14:00:00Z",
    )


def _publication_review_packet() -> dict:
    return PublicationReviewPacketContract.build_packet(
        materialization_document=_materialization_document(),
        eligibility_document=_eligibility_document(),
        reviewer_submission_document=_reviewer_submission_document(),
        candidate_review_document=_candidate_review_document(),
        prepared_by="packet@example.test",
        prepared_at="2026-07-05T15:00:00Z",
    )


def _publication_review_decision_submission(
    *, decision: str = "approve_for_governed_publication"
) -> dict:
    packet = _publication_review_packet()

    template = PublicationReviewDecisionSubmissionContract.build_template(
        packet_document=packet,
        prepared_by="publication-reviewer@example.test",
        prepared_at="2026-07-05T15:30:00Z",
    )

    template["reviewed_by_human"] = True
    template["reviewer_identity"] = "publication-reviewer@example.test"
    template["reviewed_at"] = "2026-07-05T16:00:00Z"
    template["decisions"][0]["decision"] = decision
    template["decisions"][0]["rationale"] = "Reviewed for governed publication."

    return PublicationReviewDecisionSubmissionContract.record(
        packet_document=packet,
        decision_spec=template,
    )


def _package_spec() -> dict:
    return {
        "schema_version": "1.0",
        "spec_type": "health_governed_product_knowledge_package_template_spec_v1",
        "packages": [
            {
                "package_key": "example_benefit",
                "title": "Example Benefit",
                "package_intent": "Prepare reviewed facts for human-authored explanation.",
                "packet_item_ids": [
                    _publication_review_packet()["packet_items"][0]["packet_item_id"]
                ],
            }
        ],
    }


def _package_templates(
    *, publication_decision: str = "approve_for_governed_publication"
) -> dict:
    return GovernedProductKnowledgePackageContract.build_template(
        publication_review_packet=_publication_review_packet(),
        publication_decision_submission=_publication_review_decision_submission(
            decision=publication_decision
        ),
        package_spec=_package_spec(),
        prepared_by="package@example.test",
        prepared_at="2026-07-05T17:00:00Z",
    )


def _authored_package_templates() -> dict:
    package_doc = _package_templates()
    package_doc["packages"][0]["human_authored_content"] = {
        "plain_language_explanation": "Clear explanation.",
        "simple_example": "Simple example.",
        "practical_implication": "Practical implication.",
        "applicability_notes": ["Applicability note."],
        "cautions_and_limitations": ["Caution."],
        "user_answer_boundaries": ["Boundary."],
    }
    return package_doc


def _content_review_submission() -> dict:
    package_doc = _authored_package_templates()

    template = GovernedProductKnowledgeContentReviewContract.build_review_template(
        package_templates=package_doc,
        prepared_by="content-reviewer@example.test",
        prepared_at="2026-07-05T18:00:00Z",
    )

    template["review_items"][0]["reviewer_decision"] = APPROVE_DECISION
    template["review_items"][0]["reviewer_rationale"] = "Reviewed explanation, example, cautions, and boundaries."
    template["review_items"][0]["reviewer_identity"] = "content-reviewer@example.test"
    template["review_items"][0]["reviewed_at"] = "2026-07-05T18:05:00Z"

    return GovernedProductKnowledgeContentReviewContract.record_review_submission(
        package_templates=package_doc,
        content_review_template=template,
        submitted_by="content-reviewer@example.test",
        submitted_at="2026-07-05T18:10:00Z",
    )


def test_certifies_canonical_health_trust_pipeline_creates_non_published_reusable_record():
    package_doc = _authored_package_templates()
    content_review_submission = _content_review_submission()

    records_doc = GovernedReusableProductKnowledgeRecordContract.create_records(
        package_templates=package_doc,
        content_review_submission=content_review_submission,
        created_by="record-creator@example.test",
        created_at="2026-07-05T19:00:00Z",
    )

    assert records_doc["status"] == "governed_reusable_product_knowledge_records_created_not_published"
    assert records_doc["record_count"] == 1

    record = records_doc["records"][0]
    assert record["reusable_knowledge_state"] == "created_as_governed_reusable_product_knowledge"
    assert record["publication_state"] == "not_published"
    assert record["entitlement_state"] == "not_evaluated"
    assert record["customer_answer_state"] == "not_created"
    assert record["human_reviewed_content"]["plain_language_explanation"] == "Clear explanation."


def test_certification_rejects_tampered_publication_claim_before_review():
    eligibility = _eligibility_document()
    eligibility["eligibility_records"][0]["publication_state"] = "published"

    with pytest.raises(FactPublicationEligibilityError, match="not_published"):
        FactPublicationEligibilityContract.validate_eligibility_document(eligibility)


def test_certification_rejects_deferred_fact_before_package_creation():
    with pytest.raises(GovernedProductKnowledgePackageError, match="no approved decisions"):
        _package_templates(publication_decision="defer")


def test_certification_rejects_content_review_without_human_authored_content():
    package_doc = _package_templates()

    template = GovernedProductKnowledgeContentReviewContract.build_review_template(
        package_templates=package_doc,
        prepared_by="content-reviewer@example.test",
        prepared_at="2026-07-05T18:00:00Z",
    )

    template["review_items"][0]["reviewer_decision"] = APPROVE_DECISION
    template["review_items"][0]["reviewer_rationale"] = "Trying to approve incomplete content."
    template["review_items"][0]["reviewer_identity"] = "content-reviewer@example.test"
    template["review_items"][0]["reviewed_at"] = "2026-07-05T18:05:00Z"

    with pytest.raises(GovernedProductKnowledgeContentReviewError, match="incomplete content"):
        GovernedProductKnowledgeContentReviewContract.record_review_submission(
            package_templates=package_doc,
            content_review_template=template,
            submitted_by="content-reviewer@example.test",
            submitted_at="2026-07-05T18:10:00Z",
        )


def test_certification_rejects_direct_record_creation_from_deferred_content_review():
    package_doc = _authored_package_templates()
    review = _content_review_submission()

    review["submitted_decisions"][0]["decision"] = "defer"
    review["submitted_decisions"][0]["reusable_knowledge_state"] = "blocked"

    with pytest.raises(GovernedReusableProductKnowledgeRecordError, match="no approved"):
        GovernedReusableProductKnowledgeRecordContract.create_records(
            package_templates=package_doc,
            content_review_submission=review,
            created_by="record-creator@example.test",
            created_at="2026-07-05T19:00:00Z",
        )