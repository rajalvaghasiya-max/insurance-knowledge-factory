from insurance_intelligence.contracts.evidence import EvidencePackage, Lineage
from insurance_intelligence.reasoning.rules import (
    build_rule_input,
    conditional_copayment_obligation,
)


LAB = (
    "For Doctor Prescribed Investigations - Pathology & Radiology, where reimbursement is used "
    "and the reimbursement claim was not pre-approved, a 20% co-payment applies. This assertion "
    "is limited to that investigations cover and does not establish a general product-level co-payment."
)
INTERNATIONAL = (
    "For International Cover - Emergency Care only, a mandatory 10% co-payment applies and is "
    "additional to any other co-payment or deductible applicable under the policy. This assertion "
    "is limited to the optional international emergency cover and preserves the stated stacking rule."
)
VOLUNTARY = (
    "If the Voluntary Co-payment option is selected and an In-patient Hospitalization Treatment "
    "claim is admitted, the insured bears 5%, 10%, 15%, or 20% of the eligible claim amount in "
    "proportion to the discount availed. The applicable rate therefore depends on the selected "
    "voluntary co-payment option and must not be inferred without that policy-specific selection context."
)


def _finding(statement: str):
    evidence = EvidencePackage(
        evidence_id="ev-bajaj-copay",
        requirement_id="req-bajaj-copay",
        subject_reference="product:bajaj_allianz_general:my_health_care",
        governed_entity_reference="assertion:bajaj-copay",
        field_or_topic="conditional_copayment",
        claim=statement,
        evidence_role="DEFINING",
        source_type="POLICY_WORDING",
        document_reference="bajaj_my_health_care_policy_wording_v2",
        document_version="docver-bajaj-my-health-care-v2",
        effective_from=None,
        effective_to=None,
        page=None,
        section="Conditional co-payment",
        source_excerpt=statement,
        normalized_fact_reference="bajaj-copay",
        authority_rank=1,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=Lineage(
            "source.pdf",
            "a" * 64,
            "binding.json",
            "b" * 64,
            "binding",
            "projection",
            "VERIFIED",
        ),
        retrieval_basis=("reviewed_binding", "canonical_projection"),
        confidence=1.0,
    )
    data = build_rule_input(
        requirement_id=evidence.requirement_id,
        evidence=(evidence,),
        approved_context={},
        scope="bajaj_allianz_general:my_health_care",
    )
    return conditional_copayment_obligation(data)[0]


def test_lab_copayment_keeps_reimbursement_trigger_and_cover_scope() -> None:
    finding = _finding(LAB)

    assert finding.object_or_effect == "20% of the admissible claim amount"
    assert finding.trigger == (
        "where reimbursement is used and the reimbursement claim was not pre-approved"
    )
    assert finding.applicability_scope == (
        "For Doctor Prescribed Investigations - Pathology & Radiology"
    )


def test_international_copayment_keeps_cover_scope_and_stacking_effect() -> None:
    finding = _finding(INTERNATIONAL)

    assert finding.trigger == "For International Cover - Emergency Care only"
    assert finding.applicability_scope == "For International Cover - Emergency Care only"
    assert finding.object_or_effect.startswith("10% of the admissible claim amount")
    assert "additional to any other co-payment or deductible applicable under the policy" in (
        finding.object_or_effect
    )


def test_voluntary_copayment_keeps_option_set_trigger_and_inpatient_scope() -> None:
    finding = _finding(VOLUNTARY)

    assert finding.trigger == (
        "If the Voluntary Co-payment option is selected and an In-patient Hospitalization "
        "Treatment claim is admitted"
    )
    assert finding.applicability_scope == (
        "an In-patient Hospitalization Treatment claim is admitted"
    )
    assert finding.object_or_effect == (
        "one of 5%, 10%, 15%, or 20% of the admissible claim amount, "
        "depending on the documented selected co-payment option"
    )


def test_three_bajaj_mechanisms_remain_distinct_findings() -> None:
    findings = (_finding(LAB), _finding(INTERNATIONAL), _finding(VOLUNTARY))

    assert len({item.object_or_effect for item in findings}) == 3
    assert len({item.trigger for item in findings}) == 3
    assert all(item.finding_status == "CONDITIONAL" for item in findings)
    assert all(item.derivation_type == "CONDITIONAL_DERIVATION" for item in findings)
