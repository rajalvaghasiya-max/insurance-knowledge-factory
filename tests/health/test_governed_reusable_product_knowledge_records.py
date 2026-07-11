from __future__ import annotations

import pytest

from knowledge_domains.health.extraction_primitives.governed_reusable_product_knowledge_records import (
    GovernedReusableProductKnowledgeRecordContract,
    GovernedReusableProductKnowledgeRecordError,
)


def _content():
    return {
        "plain_language_explanation": "Clear explanation.",
        "simple_example": "Simple example.",
        "practical_implication": "Practical implication.",
        "applicability_notes": ["Applicability note."],
        "cautions_and_limitations": ["Caution."],
        "user_answer_boundaries": ["Boundary."],
    }


def _package_doc():
    return {
        "schema_version": "1.0",
        "document_type": "health_governed_product_knowledge_package_template_document_v1",
        "status": "governed_product_knowledge_package_templates_prepared_pending_human_content_review",
        "template_document_id": "gpkptdoc_1",
        "source_publication_review_packet_id": "prpkt_1",
        "source_publication_decision_submission_id": "prsub_1",
        "non_publication_guardrail": "template_only_no_reusable_knowledge_publication_entitlement_or_customer_answer",
        "packages": [
            {
                "package_key": "deductible",
                "package_template_id": "gpkpt_1",
                "title": "Deductible",
                "package_intent": "Explain deductible.",
                "content_review_status": "pending_human_authoring_and_review",
                "reusable_knowledge_state": "template_only_not_created",
                "publication_state": "not_published",
                "entitlement_state": "not_evaluated",
                "non_publication_guardrail": "package_template_only_no_reusable_knowledge_publication_or_entitlement",
                "human_authored_content": _content(),
                "source_facts": [{"packet_item_id": "prpktitem_1"}],
                "source_publication_decisions": [{"decision": "approve_for_governed_publication"}],
                "source_evidence": [{"packet_item_id": "prpktitem_1"}],
            }
        ],
    }


def _review_submission():
    return {
        "schema_version": "1.0",
        "document_type": "health_governed_product_knowledge_content_review_submission_v1",
        "status": "human_content_review_decisions_recorded_not_reusable_knowledge",
        "content_review_submission_id": "gpkcrsub_1",
        "source_package_template_document_id": "gpkptdoc_1",
        "source_publication_review_packet_id": "prpkt_1",
        "source_publication_decision_submission_id": "prsub_1",
        "non_publication_guardrail": "content_review_submission_only_no_reusable_knowledge_publication_entitlement_or_customer_answer",
        "submitted_decisions": [
            {
                "content_review_decision_id": "gpkcrdec_1",
                "package_key": "deductible",
                "package_template_id": "gpkpt_1",
                "decision": "approve_for_reusable_knowledge_creation",
                "reviewer_rationale": "Approved.",
                "reviewer_identity": "reviewer",
                "reviewed_at": "2026-07-08T00:00:00Z",
                "reusable_knowledge_state": "approved_for_creation_not_created",
                "publication_state": "not_published",
                "entitlement_state": "not_evaluated",
                "non_publication_guardrail": "content_review_decision_only_no_reusable_knowledge_publication_or_entitlement",
            }
        ],
    }


def test_creates_records_from_approved_content_review():
    doc = GovernedReusableProductKnowledgeRecordContract.create_records(
        package_templates=_package_doc(),
        content_review_submission=_review_submission(),
        created_by="reviewer",
        created_at="2026-07-08T00:00:00Z",
    )
    assert doc["status"] == "governed_reusable_product_knowledge_records_created_not_published"
    assert doc["record_count"] == 1
    record = doc["records"][0]
    assert record["reusable_knowledge_state"] == "created_as_governed_reusable_product_knowledge"
    assert record["publication_state"] == "not_published"
    assert record["entitlement_state"] == "not_evaluated"
    assert record["customer_answer_state"] == "not_created"
    assert record["human_reviewed_content"]["plain_language_explanation"] == "Clear explanation."


def test_rejects_deferred_review_submission():
    review = _review_submission()
    review["submitted_decisions"][0]["decision"] = "defer"
    review["submitted_decisions"][0]["reusable_knowledge_state"] = "blocked"
    with pytest.raises(GovernedReusableProductKnowledgeRecordError, match="no approved"):
        GovernedReusableProductKnowledgeRecordContract.create_records(
            package_templates=_package_doc(),
            content_review_submission=review,
            created_by="reviewer",
            created_at="2026-07-08T00:00:00Z",
        )


def test_rejects_missing_human_content():
    package = _package_doc()
    package["packages"][0]["human_authored_content"]["simple_example"] = ""
    with pytest.raises(GovernedReusableProductKnowledgeRecordError, match="simple_example"):
        GovernedReusableProductKnowledgeRecordContract.create_records(
            package_templates=package,
            content_review_submission=_review_submission(),
            created_by="reviewer",
            created_at="2026-07-08T00:00:00Z",
        )
