from __future__ import annotations

from knowledge_domains.health.extraction_primitives.canonical_fact_materialization import (
    CanonicalFactMaterializationContract,
)
from knowledge_domains.health.extraction_primitives.fact_publication_eligibility import (
    FactPublicationEligibilityContract,
)
from knowledge_domains.health.extraction_primitives.governed_fact_selection import (
    GovernedFactSelectionContract,
)
from knowledge_domains.health.extraction_primitives.reviewer_decision_record import (
    ReviewerDecisionRecordContract,
)
from knowledge_domains.health.extraction_primitives.reviewer_decision_submission import (
    ReviewerDecisionSubmissionContract,
)


ENTITY_ID = "bajaj_allianz_general:my_health_care"
SHA = "05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158"
DOCUMENT_VERSION_ID = "docver_bajaj_my_health_care_policy_wording_v2_05dc291324340d52"
DOCUMENT_ID = "bajaj_my_health_care_policy_wording_v2"

SOURCE = {
    "entity_id": ENTITY_ID,
    "insurer_id": "bajaj_allianz_general",
    "document_type": "policy_wording",
    "source_document_id": "sha256:" + SHA,
    "sha256": SHA,
    "source_url": (
        "https://www.bajajgeneralinsurance.com/download-documents/health-insurance/"
        "Health-PW/My-Health-Care-Plan1-PW.pdf"
    ),
    "source_page_url": (
        "https://www.bajajgeneralinsurance.com/health-insurance-plans/"
        "health-insurance-documents.html"
    ),
    "relative_archive_path": (
        "archive/raw_pdf/bajaj_allianz_general/policy_wording/"
        "My-Health-Care-Plan1-PW__" + SHA + ".pdf"
    ),
    "provenance_status": "download_registry_verified",
}


def _materialization() -> dict:
    review = {
        "schema_version": "1.0",
        "review_type": "health_currency_candidate_review_document_v1",
        "review_layer": "currency_candidate_review",
        "review_layer_version": "1.0",
        "status": "review_records_generated",
        "source": SOURCE,
        "review_group_count": 1,
        "review_groups": [
            {
                "group_id": "crgrp_bajaj_v2_currentness",
                "candidate_type": "currency_amount",
                "normalized_value": {"kind": "currency", "value": 50000, "unit": "INR"},
                "inferred_scope": {
                    "benefit_scope_key": "bajaj_v2_currentness_pressure_only",
                    "band_scope_key": None,
                },
                "review_flags": ["role_selection_required"],
                "supporting_candidates": [{"candidate_id": "excand_bajaj_v2_currentness"}],
            }
        ],
    }
    pending = ReviewerDecisionRecordContract.build_pending_document(review)
    pending["decision_records"][0] = ReviewerDecisionRecordContract.build_resolved_record(
        pending["decision_records"][0],
        decision="accept",
        reviewer_identity="reviewer@policyscna.test",
        reviewed_at="2026-08-20T16:45:00Z",
        review_rationale="Bajaj v2 currentness publication-gate regression fixture.",
        selected_role="sub_limit_or_limit",
        selected_benefit_scope="bajaj_v2_currentness_pressure_only",
        selected_band_scope=None,
    )
    pending["status"] = "completed_human_review"
    submission = ReviewerDecisionSubmissionContract.build_submission_document(
        pending,
        submitted_by="submitter@policyscna.test",
        submitted_at="2026-08-20T16:46:00Z",
    )
    selection = GovernedFactSelectionContract.build_selection_document(
        submission,
        selector_identity="selector@policyscna.test",
        selected_at="2026-08-20T16:47:00Z",
    )
    return CanonicalFactMaterializationContract.build_materialization_document(
        selection,
        materialized_by="materializer@policyscna.test",
        materialized_at="2026-08-20T16:48:00Z",
    )


def _overlay(*, temporal_status: str, current_entitlement: str) -> dict:
    return {
        "schema_version": "1.0",
        "overlay_type": "document_identity_resolution_overlay_v1",
        "overlay_status": "reviewed_document_identity_resolution_recorded_not_published",
        "product_identity_reference": {"entity_id": ENTITY_ID},
        "documents": [
            {
                "document_version_link": {
                    "content_sha256": SHA,
                    "document_type": "policy_wording",
                    "document_version_id": DOCUMENT_VERSION_ID,
                    "document_id": DOCUMENT_ID,
                },
                "identity_resolution": {
                    "resolution_status": "resolved",
                    "evidence_review_eligibility": "eligible_for_evidence_review",
                    "temporal_status": temporal_status,
                    "current_entitlement_publication_eligibility": current_entitlement,
                },
            }
        ],
    }


def test_bajaj_v2_currentness_makes_fact_review_eligible_but_never_publishes() -> None:
    result = FactPublicationEligibilityContract.build_eligibility_document(
        _materialization(),
        _overlay(
            temporal_status="current_observed_reviewed",
            current_entitlement="eligible",
        ),
        validated_by="validator@policyscna.test",
        validated_at="2026-08-20T16:49:00Z",
    )

    assert result["eligible_for_publication_review_count"] == 1
    assert result["blocked_count"] == 0
    assert result["eligibility_records"][0]["eligibility_status"] == (
        "eligible_for_publication_review"
    )
    assert result["publication_state"] == "not_published"
    assert result["entitlement_state"] == "not_evaluated"
    assert result["eligibility_records"][0]["publication_state"] == "not_published"


def test_bajaj_v2_compatibility_unverified_still_blocks_review() -> None:
    result = FactPublicationEligibilityContract.build_eligibility_document(
        _materialization(),
        _overlay(
            temporal_status="compatibility_unverified",
            current_entitlement="blocked",
        ),
        validated_by="validator@policyscna.test",
        validated_at="2026-08-20T16:49:00Z",
    )

    assert result["eligible_for_publication_review_count"] == 0
    assert result["blocked_count"] == 1
    assert result["eligibility_records"][0]["eligibility_reason"] == (
        "currentness_not_eligible:compatibility_unverified"
    )
    assert result["publication_state"] == "not_published"
