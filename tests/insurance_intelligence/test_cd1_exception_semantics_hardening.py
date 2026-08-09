from dataclasses import replace

import pytest

from insurance_intelligence.contracts.evidence import EvidencePackage, Lineage
from insurance_intelligence.reasoning.rules import (
    ReasoningRuleError,
    build_rule_input,
    conditional_copayment_obligation,
)


def _evidence(claim: str) -> EvidencePackage:
    return EvidencePackage(
        evidence_id="ev-cd1-copay",
        requirement_id="req-cd1",
        subject_reference="Test Product",
        governed_entity_reference="test_insurer:test_product",
        field_or_topic="conditional_copayment",
        claim=claim,
        evidence_role="SUPPORTING",
        source_type="POLICY_WORDING",
        document_reference="test-policy-wording",
        document_version="v1",
        effective_from=None,
        effective_to=None,
        page=1,
        section="Conditional co-payment",
        source_excerpt=claim,
        normalized_fact_reference="canonical:copay",
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
        retrieval_basis=("binding", "canonical_projection"),
        confidence=0.98,
    )


def _finding(claim: str):
    item = _evidence(claim)
    data = build_rule_input(
        requirement_id="req-cd1",
        evidence=(item,),
        approved_context={},
    )
    return conditional_copayment_obligation(data)[0]


def test_unless_clause_is_separated_from_trigger() -> None:
    finding = _finding(
        "A 20% co-payment applies if treatment occurs outside the documented zone "
        "unless the treatment is an emergency hospitalization."
    )

    assert finding.trigger == "if treatment occurs outside the documented zone"
    assert finding.exception == "unless the treatment is an emergency hospitalization"
    assert "unless" not in finding.trigger.lower()


def test_except_where_clause_is_separated_from_trigger() -> None:
    finding = _finding(
        "A 15% co-payment applies when treatment occurs at a non-network hospital "
        "except where emergency admission prevents use of a network hospital."
    )

    assert finding.trigger == "when treatment occurs at a non-network hospital"
    assert finding.exception == (
        "except where emergency admission prevents use of a network hospital"
    )
    assert "except" not in finding.trigger.lower()


def test_exception_and_scope_remain_independent() -> None:
    finding = _finding(
        "A 10% co-payment applies if treatment occurs outside the preferred network "
        "unless emergency admission makes that impracticable. "
        "This co-payment is applicable only to inpatient hospitalization claims."
    )

    assert finding.trigger == "if treatment occurs outside the preferred network"
    assert finding.exception == "unless emergency admission makes that impracticable"
    assert finding.applicability_scope == (
        "This co-payment is applicable only to inpatient hospitalization claims"
    )


def test_existing_negative_exception_form_remains_supported() -> None:
    finding = _finding(
        "A 10% co-payment applies if the insured enters the policy at age 61 or above. "
        "The co-payment will not apply where the insured entered before age 61 and renewed continuously."
    )

    assert finding.trigger == "if the insured enters the policy at age 61 or above"
    assert finding.exception == (
        "The co-payment will not apply where the insured entered before age 61 and renewed continuously"
    )


def test_unextractable_exception_signal_still_fails_closed() -> None:
    item = _evidence(
        "A 10% co-payment applies if treatment occurs outside the documented network. "
        "The co-payment is waived for continuously renewed members."
    )
    item = replace(item, source_excerpt=None)
    data = build_rule_input(
        requirement_id="req-cd1",
        evidence=(item,),
        approved_context={},
    )

    with pytest.raises(ReasoningRuleError, match="signals an exception"):
        conditional_copayment_obligation(data)
