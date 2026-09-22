from __future__ import annotations

from insurance_intelligence.contracts.education_publication import (
    build_education_publication_record,
)
from insurance_intelligence.education.admission import (
    EDUCATION_ENRICHMENT,
    evaluate_education_admission,
)


def test_reviewed_education_requires_education_publication_receipt() -> None:
    publication = build_education_publication_record(
        publication_id="edu_pub_waiting_period_v1",
        governed_asset_id="meaning_waiting_period_test_v1",
        concept_id="waiting_period",
        publication_status="AUTHORITATIVE_EDUCATION",
        publication_authority="PolicyScna education publication authority",
        publication_receipt_id="edu_receipt_waiting_period_v1",
        evidence_references=("waiting_period_generic_education_v1",),
        allowed_use=EDUCATION_ENRICHMENT,
        limitations=(
            "Does not authorize product-specific mechanics.",
            "Does not determine claim approval or payment.",
        ),
    )

    decision = evaluate_education_admission(
        publication=publication,
        requested_use=EDUCATION_ENRICHMENT,
        governed_asset_id="meaning_waiting_period_test_v1",
        concept_id="waiting_period",
    )

    assert decision.admitted is True
    assert decision.publication_receipt_id == "edu_receipt_waiting_period_v1"


def test_education_publication_cannot_authorize_product_fact_use() -> None:
    publication = build_education_publication_record(
        publication_id="edu_pub_waiting_period_v1",
        governed_asset_id="meaning_waiting_period_test_v1",
        concept_id="waiting_period",
        publication_status="AUTHORITATIVE_EDUCATION",
        publication_authority="PolicyScna education publication authority",
        publication_receipt_id="edu_receipt_waiting_period_v1",
        evidence_references=("waiting_period_generic_education_v1",),
        allowed_use=EDUCATION_ENRICHMENT,
        limitations=(
            "Does not authorize product-specific mechanics.",
            "Does not determine claim approval or payment.",
        ),
    )

    decision = evaluate_education_admission(
        publication=publication,
        requested_use="PRODUCT_FACT_EVIDENCE",
        governed_asset_id="meaning_waiting_period_test_v1",
        concept_id="waiting_period",
    )

    assert decision.admitted is False
