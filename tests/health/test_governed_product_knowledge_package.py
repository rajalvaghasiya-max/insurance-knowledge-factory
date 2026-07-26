import pytest

from knowledge_domains.health.extraction_primitives.governed_product_knowledge_package import (
    GovernedProductKnowledgePackageContract,
    GovernedProductKnowledgePackageError,
)


def packet():
    return {
        "schema_version": "1.0",
        "status": "publication_review_packet_prepared_pending_human_review",
        "publication_review_packet_id": "prpkt_1",
        "non_publication_guardrail": "review_packet_only_no_approval_publication_or_reusable_knowledge",
        "packet_items": [
            {
                "packet_item_id": "item_1",
                "canonical_fact": {
                    "canonical_fact_id": "cf_1",
                    "governed_fact_id": "gf_1",
                    "canonical_field_key": "currency_sub_limit",
                    "benefit_scope": "daily_cash",
                    "normalized_value": {"kind": "currency", "value": 500, "unit": "INR"},
                    "applicability": {"sum_insured_band_scope": None},
                    "source_document": {"document_type": "policy_wording", "sha256": "abc"},
                },
                "bounded_evidence": {
                    "bounded_evidence_identity": "be_1",
                    "supporting_pages": [9],
                    "evidence_items": [{"evidence": {"text": "₹ 500 per day", "page_number": 9}}],
                },
            },
            {
                "packet_item_id": "item_2",
                "canonical_fact": {
                    "canonical_fact_id": "cf_2",
                    "governed_fact_id": "gf_2",
                    "canonical_field_key": "currency_deductible_option",
                    "benefit_scope": "annual_aggregate_deductible_option",
                    "normalized_value": {"kind": "currency", "value": 50000, "unit": "INR"},
                    "applicability": {"sum_insured_band_scope": None},
                    "source_document": {"document_type": "policy_wording", "sha256": "abc"},
                },
                "bounded_evidence": {
                    "bounded_evidence_identity": "be_2",
                    "supporting_pages": [20],
                    "evidence_items": [{"evidence": {"text": "INR 50,000 deductible", "page_number": 20}}],
                },
            },
        ],
    }


def submission():
    return {
        "schema_version": "1.0",
        "status": "human_publication_review_decisions_recorded_not_published",
        "source_publication_review_packet_id": "prpkt_1",
        "source_publication_review_packet_sha256": "sha",
        "submission_id": "prsub_1",
        "non_publication_guardrail": "decision_submission_only_no_publication_reusable_knowledge_or_entitlement",
        "submitted_decisions": [
            {
                "packet_item_id": "item_1",
                "canonical_fact_id": "cf_1",
                "governed_fact_id": "gf_1",
                "decision": "approve_for_governed_publication",
                "publication_review_decision_id": "prdec_1",
                "publication_state": "not_published",
                "entitlement_state": "not_evaluated",
                "reusable_knowledge_state": "not_created",
                "rationale": "Approved for package prep.",
                "reviewer_identity": "reviewer",
                "reviewed_at": "2026-01-01T00:00:00Z",
                "source_packet_lineage": {"publication_review_packet_id": "prpkt_1"},
            },
            {
                "packet_item_id": "item_2",
                "canonical_fact_id": "cf_2",
                "governed_fact_id": "gf_2",
                "decision": "approve_for_governed_publication",
                "publication_review_decision_id": "prdec_2",
                "publication_state": "not_published",
                "entitlement_state": "not_evaluated",
                "reusable_knowledge_state": "not_created",
                "rationale": "Approved for package prep.",
                "reviewer_identity": "reviewer",
                "reviewed_at": "2026-01-01T00:00:00Z",
                "source_packet_lineage": {"publication_review_packet_id": "prpkt_1"},
            },
        ],
    }


def spec(ids=("item_1", "item_2")):
    return {
        "schema_version": "1.0",
        "spec_type": "health_governed_product_knowledge_package_template_spec_v1",
        "packages": [
            {
                "package_key": "pilot_package",
                "title": "Pilot Package",
                "package_intent": "Prepare reviewed facts for human-authored explanation.",
                "packet_item_ids": list(ids),
            }
        ],
    }


def build(**overrides):
    return GovernedProductKnowledgePackageContract.build_template(
        publication_review_packet=overrides.get("packet", packet()),
        publication_decision_submission=overrides.get("submission", submission()),
        package_spec=overrides.get("spec", spec()),
        prepared_by="reviewer",
        prepared_at="2026-01-01T00:00:00Z",
    )


def test_template_builds_only_from_approved_items():
    document = build()
    assert document["status"] == "governed_product_knowledge_package_templates_prepared_pending_human_content_review"
    assert document["approved_packet_item_count"] == 2
    assert document["package_count"] == 1
    package = document["packages"][0]
    assert package["content_review_status"] == "pending_human_authoring_and_review"
    assert package["publication_state"] == "not_published"
    assert package["entitlement_state"] == "not_evaluated"
    assert package["human_authored_content"]["plain_language_explanation"] == ""


def test_rejects_deferred_item_in_package():
    sub = submission()
    sub["submitted_decisions"][1]["decision"] = "defer"
    with pytest.raises(GovernedProductKnowledgePackageError, match="not approved"):
        build(submission=sub)


def test_requires_all_approved_items_to_be_covered():
    with pytest.raises(GovernedProductKnowledgePackageError, match="not covered"):
        build(spec=spec(ids=("item_1",)))
