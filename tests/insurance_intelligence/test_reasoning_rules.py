from dataclasses import replace

import pytest

from insurance_intelligence.contracts.evidence import EvidencePackage, Lineage
from insurance_intelligence.reasoning.rules import (
    ReasoningRuleError,
    build_rule_input,
    conditional_copayment_nontriggered,
    conditional_copayment_obligation,
    conditional_copayment_trigger_unresolved,
    default_rule_registry,
    direct_documented_fact,
    execute_rule,
    rule_definitions,
)


def evidence(**changes):
    base = EvidencePackage(
        evidence_id="ev-copay-1",
        requirement_id="req-1",
        subject_reference="Star Comprehensive",
        governed_entity_reference="star_health:star_comprehensive",
        field_or_topic="conditional_copayment",
        claim="A 10% co-payment applies when treatment occurs in the documented city category.",
        evidence_role="SUPPORTING",
        source_type="POLICY_WORDING",
        document_reference="star-policy-wording",
        document_version="v1",
        effective_from=None,
        effective_to=None,
        page=39,
        section="Conditional co-payment",
        source_excerpt="10% co-payment applies when treatment occurs in the documented city category.",
        normalized_fact_reference="canonical:copay",
        authority_rank=3,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=Lineage("source.pdf", "a" * 64, "binding.json", "b" * 64, "binding", "projection", "VERIFIED"),
        retrieval_basis=("binding", "canonical_projection"),
        confidence=0.98,
    )
    return replace(base, **changes)


def data(*, items=None, context=None):
    return build_rule_input(requirement_id="req-1", evidence=items or (evidence(),), approved_context=context or {})


def test_build_rule_input_rejects_mismatched_requirement():
    with pytest.raises(ReasoningRuleError, match="match requirement_id"):
        build_rule_input(requirement_id="req-x", evidence=(evidence(),))


def test_build_rule_input_rejects_duplicate_evidence_ids():
    with pytest.raises(ReasoningRuleError, match="unique"):
        build_rule_input(requirement_id="req-1", evidence=(evidence(), evidence()))


def test_direct_fact_preserves_governed_claim_and_evidence():
    finding = direct_documented_fact(data())[0]
    assert finding.finding_type == "DOCUMENTED_FACT"
    assert finding.derivation_type == "DIRECT_FACT"
    assert finding.object_or_effect.startswith("A 10%")
    assert finding.evidence_ids == ("ev-copay-1",)


def test_direct_fact_skips_failed_lineage():
    item = evidence(lineage=replace(evidence().lineage, lineage_status="MISMATCH"))
    assert direct_documented_fact(data(items=(item,))) == ()


def test_direct_fact_skips_inapplicable_and_superseded_evidence():
    assert direct_documented_fact(data(items=(evidence(applicability_status="NOT_APPLICABLE"),))) == ()
    assert direct_documented_fact(data(items=(evidence(evidence_role="SUPERSEDED"),))) == ()


def test_direct_fact_order_is_deterministic():
    second = evidence(evidence_id="ev-copay-2", authority_rank=2, claim="Second governed fact.")
    first = evidence(evidence_id="ev-copay-1", authority_rank=3)
    result = direct_documented_fact(data(items=(first, second)))
    assert [item.evidence_ids[0] for item in result] == ["ev-copay-2", "ev-copay-1"]


def test_copayment_obligation_extracts_percentage_not_hardcoded():
    item = evidence(claim="A 17.5% co-payment applies if treatment occurs outside the network.")
    finding = conditional_copayment_obligation(data(items=(item,)))[0]
    assert finding.object_or_effect == "17.5% of the admissible claim amount"
    assert finding.condition == "if treatment occurs outside the network"
    assert finding.finding_status == "CONDITIONAL"


def test_copayment_obligation_is_evidence_linked():
    finding = conditional_copayment_obligation(data())[0]
    assert finding.finding_type == "CLAIM_COST_SHARING"
    assert finding.subject == "insured"
    assert finding.predicate == "must_bear"
    assert finding.evidence_ids == ("ev-copay-1",)


def test_copayment_rule_rejects_missing_percentage():
    with pytest.raises(ReasoningRuleError, match="percentage"):
        conditional_copayment_obligation(data(items=(evidence(claim="Co-payment applies when treatment occurs elsewhere.", source_excerpt=None),)))


def test_copayment_rule_rejects_missing_condition():
    item = evidence(claim="A 10% co-payment applies.", source_excerpt="10% co-payment.", section="conditional_copayment")
    with pytest.raises(ReasoningRuleError, match="trigger condition"):
        conditional_copayment_obligation(data(items=(item,)))


def test_copayment_rule_rejects_no_usable_evidence():
    item = evidence(lineage=replace(evidence().lineage, lineage_status="MISSING"))
    with pytest.raises(ReasoningRuleError, match="no usable"):
        conditional_copayment_obligation(data(items=(item,)))


def test_nontriggered_requires_explicit_approved_context():
    with pytest.raises(ReasoningRuleError, match="NOT_TRIGGERED"):
        conditional_copayment_nontriggered(data())


def test_nontriggered_finding_does_not_erase_general_clause():
    finding = conditional_copayment_nontriggered(data(context={"conditional_copayment_trigger_status": "NOT_TRIGGERED"}))[0]
    assert finding.finding_status == "SUPPORTED"
    assert finding.predicate == "is_not_triggered"
    assert "approved context" in finding.condition
    assert "no co-payment" not in finding.object_or_effect.lower()


def test_unresolved_trigger_produces_partial_finding():
    finding = conditional_copayment_trigger_unresolved(data())[0]
    assert finding.finding_type == "UNRESOLVED_IMPLICATION"
    assert finding.finding_status == "PARTIALLY_SUPPORTED"
    assert finding.limitations


def test_unresolved_trigger_rejects_confirmed_context():
    with pytest.raises(ReasoningRuleError, match="UNRESOLVED"):
        conditional_copayment_trigger_unresolved(data(context={"conditional_copayment_trigger_status": "CONFIRMED"}))


def test_execute_rule_dispatches_registered_executor():
    assert execute_rule("conditional_copayment_obligation_v1", data())[0].rule_id == "conditional_copayment_obligation_v1"


def test_execute_rule_rejects_unknown_rule():
    with pytest.raises(ReasoningRuleError, match="unregistered"):
        execute_rule("free_form_reasoning", data())


def test_rule_definitions_are_versioned_and_unique():
    definitions = rule_definitions()
    assert len({item.rule_id for item in definitions}) == len(definitions)
    assert {item.rule_version for item in definitions} == {"1.0"}


def test_default_registry_orders_rules_deterministically():
    ids = [item.rule_id for item in default_rule_registry().all_rules()]
    assert ids == [
        "direct_documented_fact_v1",
        "conditional_copayment_obligation_v1",
        "conditional_copayment_nontriggered_v1",
        "conditional_copayment_trigger_unresolved_v1",
    ]


def test_identical_inputs_produce_identical_finding_ids():
    first = conditional_copayment_obligation(data())[0]
    second = conditional_copayment_obligation(data())[0]
    assert first == second


def test_rule_does_not_calculate_rupee_amount():
    finding = conditional_copayment_obligation(data())[0]
    assert "₹" not in finding.object_or_effect
    assert "rupee" not in finding.object_or_effect.lower()
    assert finding.derivation_type != "CALCULATION"


def test_rule_input_and_evidence_are_not_mutated():
    item = evidence()
    original = item
    context = {"conditional_copayment_trigger_status": "UNRESOLVED"}
    built = build_rule_input(requirement_id="req-1", evidence=(item,), approved_context=context)
    conditional_copayment_trigger_unresolved(built)
    assert item == original
    assert context == {"conditional_copayment_trigger_status": "UNRESOLVED"}


def test_rule_outputs_contain_no_recommendation_or_final_answer_fields():
    finding = conditional_copayment_obligation(data())[0]
    assert not hasattr(finding, "recommendation")
    assert not hasattr(finding, "answer")
    assert not hasattr(finding, "explanation")
