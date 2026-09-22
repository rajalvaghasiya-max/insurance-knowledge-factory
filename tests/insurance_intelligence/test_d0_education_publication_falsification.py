from __future__ import annotations

import pytest

from insurance_intelligence.contracts.education_publication import (
    CUSTOMER_EDUCATION,
    OPERATIVE_PRODUCT_FACT,
    build_education_publication_input,
)
from insurance_intelligence.education_publication.admission import (
    evaluate_education_admission,
)
from insurance_intelligence.education_publication.gate import (
    create_education_publication,
)
from insurance_intelligence.evidence.admission import (
    EvidenceAdmissionError,
    USER_ANSWER,
    evaluate_publication_admission,
)


def _reviewed_meaning_asset() -> dict:
    return {
        "asset_id": "meaning_waiting_period_test",
        "asset_type": "meaning_asset",
        "schema_version": "meaning_asset_v1.0",
        "asset_version": "1.0",
        "concept_id": "waiting_period",
        "canonical_name": "Waiting Period",
        "category": "coverage_activation_timeline",
        "core_meaning": (
            "A waiting period is a policy-defined period during which a specified "
            "coverage restriction applies."
        ),
        "business_purpose": (
            "It helps explain when a specified restriction applies without deciding "
            "claim approval or payment."
        ),
        "functional_behaviour": (
            "The applicable policy wording determines what is restricted, for how long, "
            "and which exceptions or continuity rules apply."
        ),
        "trigger": "A governed waiting-period rule applies to a specified condition.",
        "inputs": ["policy_terms"],
        "outputs": ["waiting_period_applicability_state"],
        "calculation_basis": "No exact boundary convention is invented.",
        "dependencies": ["policy_terms"],
        "constraints": [
            "This does not determine claim approval or claim payment.",
        ],
        "exceptions": [
            "No generic exception is asserted without governed product evidence.",
        ],
        "relationships": {
            "depends_on": ["policy_terms"],
            "related_to": ["initial_waiting_period"],
            "commonly_confused_with": ["permanent_exclusion"],
        },
        "misinterpretations": [],
        "policy_examples": [
            {
                "scenario": "A policy contains a waiting-period clause.",
                "result": (
                    "The restriction can still apply during the applicable period. "
                    "This does not determine claim approval or claim payment."
                ),
                "source_example": {
                    "scenario": "A policy contains a waiting-period clause.",
                    "result": "The restriction can still apply.",
                    "boundary": (
                        "Illustrative only. This does not determine claim approval "
                        "or claim payment."
                    ),
                },
            }
        ],
        "confidence": {
            "canonical_confidence": 1.0,
            "requires_review": False,
            "review_basis": "approved_governed_generic_concept_record",
        },
        "evidence_refs": ["generic_waiting_period_evidence_v1"],
        "evidence": [
            {
                "evidence_id": "generic_waiting_period_evidence_v1",
                "source_type": "approved_training_material",
                "source_title": "Reviewed waiting-period concept source",
                "publisher": "PolicyScna test governance",
                "source_locator": "test://waiting-period",
                "source_sha256": "a" * 64,
                "evidence_text": "Reviewed generic waiting-period concept evidence.",
                "evidence_scope": "generic_insurance_concept",
            }
        ],
        "review_status": "approved_governed_generic_concept",
        "certification": {
            "status": "governed_source_approved",
            "human_reviewed": True,
            "review_decision_id": "review_waiting_period_v1",
        },
        "governance": {
            "source_governed_record_id": "gconcept_waiting_period_v1",
            "source_record_type": "governed_generic_concept_record_v0_2",
            "source_schema_version": "0.2",
            "source_knowledge_version": "1.0",
            "concept_scope": "generic_insurance_concept",
            "publication_state": "not_published",
            "customer_answer_state": "not_created",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
            "review_decision": {
                "review_decision_id": "review_waiting_period_v1",
                "decision": "approve_for_governed_generic_concept_creation",
                "reviewer_identity": "reviewer",
                "reviewed_at": "2026-09-20T00:00:00Z",
                "rationale": "Reviewed for generic education use.",
            },
            "product_specific_boundary": (
                "Product mechanics must come from governed product knowledge."
            ),
            "customer_document_boundary": (
                "Customer-specific facts must come from applicable customer documents."
            ),
        },
        "factory_signature": {
            "factory": "PolicyScna Knowledge Factory",
            "production_line": "GovernedConceptToMeaningAssetAdapter",
            "adapter_version": "1.0",
            "schema_version": "meaning_asset_v1.0",
            "deterministic": True,
        },
        "notes": ["Education source asset only."],
    }


def test_reviewed_education_requires_explicit_publication_receipt() -> None:
    source = _reviewed_meaning_asset()

    publication = create_education_publication(
        build_education_publication_input(
            publication_id="education_pub_waiting_period_v1",
            meaning_asset=source,
            publication_authority="PolicyScna education publication authority",
        )
    )

    assert publication.publication_receipt_id
    assert publication.allowed_uses == (CUSTOMER_EDUCATION,)

    decision = evaluate_education_admission(
        publication=publication,
        requested_use=CUSTOMER_EDUCATION,
        concept_id="waiting_period",
    )
    assert decision.admitted is True


def test_education_publication_cannot_authorize_operative_product_fact_use() -> None:
    publication = create_education_publication(
        build_education_publication_input(
            publication_id="education_pub_waiting_period_v1",
            meaning_asset=_reviewed_meaning_asset(),
            publication_authority="PolicyScna education publication authority",
        )
    )

    decision = evaluate_education_admission(
        publication=publication,
        requested_use=OPERATIVE_PRODUCT_FACT,
        concept_id="waiting_period",
    )
    assert decision.admitted is False


def test_education_publication_cannot_masquerade_as_authoritative_product_evidence() -> None:
    publication = create_education_publication(
        build_education_publication_input(
            publication_id="education_pub_waiting_period_v1",
            meaning_asset=_reviewed_meaning_asset(),
            publication_authority="PolicyScna education publication authority",
        )
    )

    with pytest.raises(EvidenceAdmissionError):
        evaluate_publication_admission(
            evidence_use=USER_ANSWER,
            publication=publication,  # type: ignore[arg-type]
        )
