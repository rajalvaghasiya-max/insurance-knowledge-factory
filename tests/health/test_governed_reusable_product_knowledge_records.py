from __future__ import annotations

import copy

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
                "source_facts": [{"packet_item_id": "prpktitem_1", "governed_fact_id": "gfact_1"}],
                "source_publication_decisions": [{"decision": "approve_for_governed_publication"}],
                "source_evidence": [{"packet_item_id": "prpktitem_1", "bounded_evidence_identity": "bevid_1"}],
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


def _second_package(package_key="copay"):
    package = copy.deepcopy(_package_doc()["packages"][0])
    package["package_key"] = package_key
    package["package_template_id"] = f"gpkpt_{package_key}"
    package["title"] = package_key.title()
    package["source_facts"] = [{"packet_item_id": f"pi_{package_key}", "governed_fact_id": f"gfact_{package_key}"}]
    package["source_evidence"] = [{"packet_item_id": f"pi_{package_key}", "bounded_evidence_identity": f"bevid_{package_key}"}]
    return package


def _second_decision(package_key="copay"):
    decision = copy.deepcopy(_review_submission()["submitted_decisions"][0])
    decision["content_review_decision_id"] = f"gpkcrdec_{package_key}"
    decision["package_key"] = package_key
    decision["package_template_id"] = f"gpkpt_{package_key}"
    return decision


def test_repeated_identical_input_produces_identical_semantic_output():
    """3.7 determinism: identical governed input must produce identical output."""
    doc_a = GovernedReusableProductKnowledgeRecordContract.create_records(
        package_templates=_package_doc(),
        content_review_submission=_review_submission(),
        created_by="reviewer",
        created_at="2026-07-08T00:00:00Z",
    )
    doc_b = GovernedReusableProductKnowledgeRecordContract.create_records(
        package_templates=_package_doc(),
        content_review_submission=_review_submission(),
        created_by="reviewer",
        created_at="2026-07-08T00:00:00Z",
    )
    assert doc_a == doc_b


def test_input_order_does_not_alter_output_order_or_document_id():
    """Two package/decision orderings covering the same semantic set of approved
    packages must yield the same record order and the same record_document_id.
    Per-record reusable_knowledge_record_id must also be unaffected by order."""
    package_doc_forward = _package_doc()
    package_doc_forward["packages"].append(_second_package("copay"))
    review_forward = _review_submission()
    review_forward["submitted_decisions"].append(_second_decision("copay"))

    package_doc_reversed = _package_doc()
    package_doc_reversed["packages"] = [_second_package("copay"), package_doc_reversed["packages"][0]]
    review_reversed = _review_submission()
    review_reversed["submitted_decisions"] = [_second_decision("copay"), review_reversed["submitted_decisions"][0]]

    doc_forward = GovernedReusableProductKnowledgeRecordContract.create_records(
        package_templates=package_doc_forward,
        content_review_submission=review_forward,
        created_by="reviewer",
        created_at="2026-07-08T00:00:00Z",
    )
    doc_reversed = GovernedReusableProductKnowledgeRecordContract.create_records(
        package_templates=package_doc_reversed,
        content_review_submission=review_reversed,
        created_by="reviewer",
        created_at="2026-07-08T00:00:00Z",
    )

    assert [r["package_key"] for r in doc_forward["records"]] == [r["package_key"] for r in doc_reversed["records"]]
    assert doc_forward["record_document_id"] == doc_reversed["record_document_id"]
    forward_ids = {r["package_key"]: r["reusable_knowledge_record_id"] for r in doc_forward["records"]}
    reversed_ids = {r["package_key"]: r["reusable_knowledge_record_id"] for r in doc_reversed["records"]}
    assert forward_ids == reversed_ids


def test_missing_governed_fact_selection_fails_safely():
    """A package with no backing source_facts (no governed fact was ever selected)
    must not be allowed to become a reusable knowledge record."""
    package = _package_doc()
    package["packages"][0]["source_facts"] = []
    with pytest.raises(GovernedReusableProductKnowledgeRecordError, match="source_facts must not be empty"):
        GovernedReusableProductKnowledgeRecordContract.create_records(
            package_templates=package,
            content_review_submission=_review_submission(),
            created_by="reviewer",
            created_at="2026-07-08T00:00:00Z",
        )


def test_missing_product_identity_on_source_fact_fails_safely():
    """A source_fact entry without a governed_fact_id carries no verifiable
    identity linkage back to a governed fact and must be rejected."""
    package = _package_doc()
    package["packages"][0]["source_facts"] = [{"packet_item_id": "prpktitem_1"}]
    with pytest.raises(GovernedReusableProductKnowledgeRecordError, match="governed_fact_id"):
        GovernedReusableProductKnowledgeRecordContract.create_records(
            package_templates=package,
            content_review_submission=_review_submission(),
            created_by="reviewer",
            created_at="2026-07-08T00:00:00Z",
        )


def test_unpublished_or_review_required_facts_are_not_upgraded():
    """A package whose reusable_knowledge_state has already moved past
    'template_only_not_created' must not be silently re-processed into a
    created record (no governance-state upgrade may be smuggled through)."""
    package = _package_doc()
    package["packages"][0]["reusable_knowledge_state"] = "created_as_governed_reusable_product_knowledge"
    with pytest.raises(GovernedReusableProductKnowledgeRecordError, match="reusable knowledge state is invalid"):
        GovernedReusableProductKnowledgeRecordContract.create_records(
            package_templates=package,
            content_review_submission=_review_submission(),
            created_by="reviewer",
            created_at="2026-07-08T00:00:00Z",
        )


def test_invalid_evidence_reference_is_rejected():
    """source_evidence entries without a bounded_evidence_identity are not
    valid evidence references and must not be preserved into a governed record."""
    package = _package_doc()
    package["packages"][0]["source_evidence"] = [{"packet_item_id": "prpktitem_1"}]
    with pytest.raises(GovernedReusableProductKnowledgeRecordError, match="bounded_evidence_identity"):
        GovernedReusableProductKnowledgeRecordContract.create_records(
            package_templates=package,
            content_review_submission=_review_submission(),
            created_by="reviewer",
            created_at="2026-07-08T00:00:00Z",
        )


def test_empty_evidence_list_is_rejected():
    """A package with zero evidence entries has no support at all and must
    not be allowed to become governed reusable knowledge (evidence before
    explanation)."""
    package = _package_doc()
    package["packages"][0]["source_evidence"] = []
    with pytest.raises(GovernedReusableProductKnowledgeRecordError, match="source_evidence must not be empty"):
        GovernedReusableProductKnowledgeRecordContract.create_records(
            package_templates=package,
            content_review_submission=_review_submission(),
            created_by="reviewer",
            created_at="2026-07-08T00:00:00Z",
        )


def test_duplicate_package_key_in_package_templates_is_rejected():
    """Two package template entries sharing the same package_key represent
    ambiguous input and must not be silently collapsed into one record."""
    package = _package_doc()
    duplicate = copy.deepcopy(package["packages"][0])
    duplicate["title"] = "Conflicting duplicate"
    package["packages"].append(duplicate)
    with pytest.raises(GovernedReusableProductKnowledgeRecordError, match="duplicate package_key"):
        GovernedReusableProductKnowledgeRecordContract.create_records(
            package_templates=package,
            content_review_submission=_review_submission(),
            created_by="reviewer",
            created_at="2026-07-08T00:00:00Z",
        )


def test_duplicate_approved_decisions_do_not_create_duplicate_records():
    """The same package_key approved twice in submitted_decisions must not
    produce two reusable records for that package."""
    review = _review_submission()
    review["submitted_decisions"].append(copy.deepcopy(review["submitted_decisions"][0]))
    with pytest.raises(GovernedReusableProductKnowledgeRecordError, match="duplicate approved decision"):
        GovernedReusableProductKnowledgeRecordContract.create_records(
            package_templates=_package_doc(),
            content_review_submission=review,
            created_by="reviewer",
            created_at="2026-07-08T00:00:00Z",
        )


def test_changed_source_lineage_triggers_revalidation_rejection():
    """If the package templates document's identity changes (e.g. was
    regenerated), a content review submission still pointing at the old
    template_document_id must be rejected rather than silently accepted."""
    package = _package_doc()
    package["template_document_id"] = "gpkptdoc_2_changed"
    with pytest.raises(GovernedReusableProductKnowledgeRecordError, match="does not belong to"):
        GovernedReusableProductKnowledgeRecordContract.create_records(
            package_templates=package,
            content_review_submission=_review_submission(),
            created_by="reviewer",
            created_at="2026-07-08T00:00:00Z",
        )


def test_output_never_claims_entitlement_publication_or_customer_answer():
    """Governance-boundary regression: this stage must never upgrade a
    record's publication, entitlement, or customer-answer state, and must
    disclose its non-publication guardrail and limitations."""
    doc = GovernedReusableProductKnowledgeRecordContract.create_records(
        package_templates=_package_doc(),
        content_review_submission=_review_submission(),
        created_by="reviewer",
        created_at="2026-07-08T00:00:00Z",
    )
    record = doc["records"][0]
    assert record["publication_state"] == "not_published"
    assert record["entitlement_state"] == "not_evaluated"
    assert record["customer_answer_state"] == "not_created"
    assert doc["readiness"]["publication"] == "not_published"
    assert doc["readiness"]["entitlement"] == "not_evaluated"
    assert doc["readiness"]["customer_answer"] == "not_created"
