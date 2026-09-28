from __future__ import annotations

from insurance_intelligence.contracts.reasoning import (
    build_customer_qualification,
    build_finding,
)
from insurance_intelligence.explanation.templates import (
    _customer_communication_sections,
    _plain_finding_text,
)


def test_customer_composition_omits_not_applicable_qualification_by_typed_provenance() -> None:
    applicable = build_customer_qualification(
        qualification_id="qualification-applicable",
        text="Applicable synthetic qualification.",
        applicability_status="APPLICABLE",
        evidence_ids=("evidence-a",),
    )
    not_applicable = build_customer_qualification(
        qualification_id="qualification-not-applicable",
        text="Non-applicable synthetic qualification.",
        applicability_status="NOT_APPLICABLE",
        evidence_ids=("evidence-b",),
    )
    finding = build_finding(
        finding_id="finding-synthetic",
        requirement_id="requirement-synthetic",
        finding_type="CLAIM_CONDITION",
        subject="synthetic restriction",
        predicate="is_still_active",
        object_or_effect="the synthetic restriction is still active",
        scope="product",
        finding_status="SUPPORTED",
        derivation_type="DETERMINISTIC_DERIVATION",
        rule_id="synthetic_rule_v1",
        rule_version="1.0",
        evidence_ids=("evidence-a", "evidence-b"),
        exception="Non-applicable synthetic qualification.",
        applicability_scope="Synthetic machine-only scope.",
        customer_qualifications=(applicable, not_applicable),
    )

    sections = _customer_communication_sections(
        request_id="request-synthetic",
        finding=finding,
    )

    assert tuple(item.text for item in sections) == (
        "Applicable synthetic qualification.",
    )
    assert finding.customer_qualifications == (applicable, not_applicable)
    assert finding.exception == "Non-applicable synthetic qualification."
    assert finding.applicability_scope == "Synthetic machine-only scope."

    customer_text = _plain_finding_text(finding, audience="CUSTOMER")
    advisor_text = _plain_finding_text(finding, audience="ADVISOR")
    assert "Non-applicable synthetic qualification" not in customer_text
    assert "Synthetic machine-only scope" not in customer_text
    assert "Non-applicable synthetic qualification" in advisor_text
    assert "Synthetic machine-only scope" in advisor_text
