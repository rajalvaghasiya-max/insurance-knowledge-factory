from __future__ import annotations

from dataclasses import fields

from insurance_intelligence.contracts import reasoning as reasoning_contract


def test_customer_qualification_applicability_is_typed_and_preserved_per_qualification() -> None:
    assert hasattr(reasoning_contract, "CustomerQualification")
    assert hasattr(reasoning_contract, "CUSTOMER_QUALIFICATION_APPLICABILITY")

    qualification_fields = {
        item.name for item in fields(reasoning_contract.CustomerQualification)
    }
    assert {
        "qualification_id",
        "text",
        "applicability_status",
        "evidence_ids",
    } <= qualification_fields
    assert {
        "APPLICABLE",
        "NOT_APPLICABLE",
        "UNRESOLVED",
    } <= reasoning_contract.CUSTOMER_QUALIFICATION_APPLICABILITY

    finding_fields = {item.name for item in fields(reasoning_contract.Finding)}
    assert "customer_qualifications" in finding_fields


def test_customer_surface_can_distinguish_qualification_applicability_without_text_matching() -> None:
    assert hasattr(reasoning_contract, "build_customer_qualification")

    applicable = reasoning_contract.build_customer_qualification(
        qualification_id="qualification-applicable",
        text="A governed qualification that applies to this synthetic case.",
        applicability_status="APPLICABLE",
        evidence_ids=("evidence-a",),
    )
    not_applicable = reasoning_contract.build_customer_qualification(
        qualification_id="qualification-not-applicable",
        text="A governed qualification that does not apply to this synthetic case.",
        applicability_status="NOT_APPLICABLE",
        evidence_ids=("evidence-b",),
    )

    assert applicable.applicability_status == "APPLICABLE"
    assert not_applicable.applicability_status == "NOT_APPLICABLE"
    assert applicable.evidence_ids == ("evidence-a",)
    assert not_applicable.evidence_ids == ("evidence-b",)
