from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

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
    EducationPublicationGateError,
    create_education_publication,
)
from insurance_intelligence.evidence.admission import (
    EvidenceAdmissionError,
    USER_ANSWER,
    evaluate_publication_admission,
)


def reviewed_meaning_asset() -> dict:
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
            "This generic concept does not determine claim approval or claim payment.",
            "Product mechanics must come from governed product knowledge.",
            "Customer-specific facts must come from applicable customer documents.",
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
                    "result": "The restriction can still apply during the applicable period.",
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
                "source_type": "insurer_policy_wording_standard_definition",
                "source_title": "Reviewed waiting-period concept source",
                "publisher": "Example insurer",
                "source_locator": "knowledge/example/policy_wording.json::$.definition",
                "source_document_path": "knowledge/example/policy_wording.pdf",
                "source_sha256": "a" * 64,
                "evidence_text": "Reviewed generic waiting-period concept evidence.",
                "hosting_document_scope": "product_specific",
                "extracted_content_scope": "generic_insurance_concept",
                "product_context_excluded": True,
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


def publish(asset: dict | None = None):
    return create_education_publication(
        build_education_publication_input(
            publication_id="education_pub_waiting_period_v1",
            meaning_asset=asset or reviewed_meaning_asset(),
            publication_authority="PolicyScna education publication authority",
        )
    )


def test_reviewed_education_requires_explicit_publication_receipt() -> None:
    publication = publish()

    assert publication.publication_receipt_id.startswith("education_receipt_")
    assert publication.allowed_uses == (CUSTOMER_EDUCATION,)
    assert publication.definition.startswith("A waiting period")
    assert publication.examples[0].boundary.startswith("Illustrative only")

    decision = evaluate_education_admission(
        publication=publication,
        requested_use=CUSTOMER_EDUCATION,
        concept_id="waiting_period",
    )
    assert decision.admitted is True


def test_missing_publication_is_not_admitted_for_customer_education() -> None:
    decision = evaluate_education_admission(
        publication=None,
        requested_use=CUSTOMER_EDUCATION,
        concept_id="waiting_period",
    )
    assert decision.admitted is False
    assert "explicit education publication receipt" in decision.basis


def test_missing_receipt_fails_closed() -> None:
    publication = replace(publish(), publication_receipt_id="")
    decision = evaluate_education_admission(
        publication=publication,
        requested_use=CUSTOMER_EDUCATION,
        concept_id="waiting_period",
    )
    assert decision.admitted is False
    assert "receipt is missing" in decision.basis


def test_education_publication_cannot_authorize_operative_product_fact_use() -> None:
    decision = evaluate_education_admission(
        publication=publish(),
        requested_use=OPERATIVE_PRODUCT_FACT,
        concept_id="waiting_period",
    )
    assert decision.admitted is False


def test_education_publication_cannot_masquerade_as_product_evidence() -> None:
    publication = publish()

    with pytest.raises(EvidenceAdmissionError):
        evaluate_publication_admission(
            evidence_use=USER_ANSWER,
            publication=publication,  # type: ignore[arg-type]
        )


def test_publication_receipt_is_deterministic_and_source_is_not_mutated() -> None:
    source = reviewed_meaning_asset()
    original = deepcopy(source)

    first = publish(source)
    second = publish(source)

    assert first == second
    assert source == original


def test_unreviewed_source_fails_closed() -> None:
    source = reviewed_meaning_asset()
    source["certification"]["human_reviewed"] = False

    with pytest.raises(EducationPublicationGateError, match="human reviewed"):
        publish(source)


def test_product_context_must_be_excluded_from_product_hosted_generic_evidence() -> None:
    source = reviewed_meaning_asset()
    source["evidence"][0]["product_context_excluded"] = False

    with pytest.raises(EducationPublicationGateError, match="exclude product context"):
        publish(source)


def test_affirmative_claim_payment_language_is_not_publishable() -> None:
    source = reviewed_meaning_asset()
    source["business_purpose"] = "The insurer will pay the claim after this period."

    with pytest.raises(EducationPublicationGateError, match="claim-payment"):
        publish(source)


def test_recommendation_language_is_not_publishable() -> None:
    source = reviewed_meaning_asset()
    source["functional_behaviour"] = "You should buy the policy when this rule applies."

    with pytest.raises(EducationPublicationGateError, match="recommendation"):
        publish(source)


def test_concept_mismatch_is_not_admitted() -> None:
    decision = evaluate_education_admission(
        publication=publish(),
        requested_use=CUSTOMER_EDUCATION,
        concept_id="copay",
    )
    assert decision.admitted is False
    assert "concept does not match" in decision.basis
