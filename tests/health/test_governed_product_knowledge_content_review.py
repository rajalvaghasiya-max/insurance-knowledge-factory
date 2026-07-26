from __future__ import annotations

import pytest

from knowledge_domains.health.extraction_primitives.governed_product_knowledge_content_review import (
    APPROVE_DECISION,
    GovernedProductKnowledgeContentReviewContract,
    GovernedProductKnowledgeContentReviewError,
)


def _package_doc() -> dict:
    content = {
        "plain_language_explanation": "Explains the reviewed package in plain language.",
        "simple_example": "Shows a cautious illustrative example.",
        "practical_implication": "Explains a practical implication without entitlement.",
        "applicability_notes": ["Applies only under the reviewed scope."],
        "cautions_and_limitations": ["Do not treat as customer-specific entitlement."],
        "user_answer_boundaries": ["Use only for generic explanation unless schedule is checked."],
    }
    package = {
        "package_template_id": "gpkpt_1",
        "package_key": "annual_aggregate_deductible_options",
        "title": "Annual aggregate deductible options",
        "human_authored_content": content,
        "content_review_status": "pending_human_authoring_and_review",
        "reusable_knowledge_state": "template_only_not_created",
        "publication_state": "not_published",
        "entitlement_state": "not_evaluated",
        "non_publication_guardrail": "package_template_only_no_reusable_knowledge_publication_or_entitlement",
        "source_facts": [{"packet_item_id": "prpktitem_1"}],
        "source_publication_decisions": [{"packet_item_id": "prpktitem_1"}],
        "source_evidence": [{"packet_item_id": "prpktitem_1"}],
    }
    return {
        "schema_version": "1.0",
        "document_type": "health_governed_product_knowledge_package_template_document_v1",
        "status": "governed_product_knowledge_package_templates_prepared_pending_human_content_review",
        "template_document_id": "gpkptdoc_1",
        "source_publication_review_packet_id": "prpkt_1",
        "source_publication_decision_submission_id": "prsub_1",
        "packages": [package],
        "non_publication_guardrail": "template_only_no_reusable_knowledge_publication_entitlement_or_customer_answer",
    }


def test_builds_content_review_template_for_complete_authored_package():
    template = GovernedProductKnowledgeContentReviewContract.build_review_template(
        package_templates=_package_doc(),
        prepared_by="rajal_vaghasiya",
        prepared_at="2026-07-08T00:00:00Z",
    )

    assert template["status"] == "content_review_template_prepared_pending_human_review"
    assert template["package_count"] == 1
    assert template["complete_content_package_count"] == 1
    assert template["review_items"][0]["recommended_decision"] == APPROVE_DECISION
    assert template["non_publication_guardrail"] == "content_review_template_only_no_reusable_knowledge_publication_entitlement_or_customer_answer"


def test_records_review_submission_without_creating_reusable_knowledge():
    package_doc = _package_doc()
    template = GovernedProductKnowledgeContentReviewContract.build_review_template(
        package_templates=package_doc,
        prepared_by="rajal_vaghasiya",
        prepared_at="2026-07-08T00:00:00Z",
    )
    template["review_items"][0]["reviewer_decision"] = APPROVE_DECISION
    template["review_items"][0]["reviewer_rationale"] = "Reviewed explanation, example, cautions, and boundaries."
    template["review_items"][0]["reviewer_identity"] = "rajal_vaghasiya"
    template["review_items"][0]["reviewed_at"] = "2026-07-08T00:05:00Z"

    submission = GovernedProductKnowledgeContentReviewContract.record_review_submission(
        package_templates=package_doc,
        content_review_template=template,
        submitted_by="rajal_vaghasiya",
        submitted_at="2026-07-08T00:06:00Z",
    )

    assert submission["status"] == "human_content_review_decisions_recorded_not_reusable_knowledge"
    assert submission["decision_counts"][APPROVE_DECISION] == 1
    decision = submission["submitted_decisions"][0]
    assert decision["reusable_knowledge_state"] == "approved_for_creation_not_created"
    assert decision["publication_state"] == "not_published"
    assert decision["entitlement_state"] == "not_evaluated"


def test_cannot_approve_incomplete_content():
    package_doc = _package_doc()
    package_doc["packages"][0]["human_authored_content"]["simple_example"] = ""
    template = GovernedProductKnowledgeContentReviewContract.build_review_template(
        package_templates=package_doc,
        prepared_by="rajal_vaghasiya",
        prepared_at="2026-07-08T00:00:00Z",
    )
    template["review_items"][0]["reviewer_decision"] = APPROVE_DECISION
    template["review_items"][0]["reviewer_rationale"] = "Trying to approve incomplete content."
    template["review_items"][0]["reviewer_identity"] = "rajal_vaghasiya"
    template["review_items"][0]["reviewed_at"] = "2026-07-08T00:05:00Z"

    with pytest.raises(GovernedProductKnowledgeContentReviewError, match="cannot be approved with incomplete content"):
        GovernedProductKnowledgeContentReviewContract.record_review_submission(
            package_templates=package_doc,
            content_review_template=template,
            submitted_by="rajal_vaghasiya",
            submitted_at="2026-07-08T00:06:00Z",
        )
