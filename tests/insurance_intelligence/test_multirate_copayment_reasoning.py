from dataclasses import replace

from insurance_intelligence.contracts.evidence import EvidencePackage, Lineage
from insurance_intelligence.reasoning.rules import (
    build_rule_input,
    conditional_copayment_obligation,
)


def _evidence(claim: str) -> EvidencePackage:
    return EvidencePackage(
        evidence_id="ev-multirate-copay",
        requirement_id="req-multirate-copay",
        subject_reference="product:test",
        governed_entity_reference="assertion:test-copay",
        field_or_topic="conditional_copayment",
        claim=claim,
        evidence_role="SUPPORTING",
        source_type="POLICY_WORDING",
        document_reference="policy-wording-v1",
        document_version="docver-v1",
        effective_from=None,
        effective_to=None,
        page=1,
        section="Conditional co-payment",
        source_excerpt=claim,
        normalized_fact_reference="canonical:test-copay",
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
        confidence=1.0,
    )


def _finding(claim: str):
    evidence = _evidence(claim)
    data = build_rule_input(
        requirement_id=evidence.requirement_id,
        evidence=(evidence,),
        approved_context={},
    )
    return conditional_copayment_obligation(data)[0]


def test_single_rate_copayment_behavior_remains_unchanged() -> None:
    finding = _finding(
        "A 10% co-payment applies if the documented eligibility condition is met."
    )

    assert finding.object_or_effect == "10% of the admissible claim amount"
    assert finding.trigger == "if the documented eligibility condition is met"
    assert finding.finding_status == "CONDITIONAL"


def test_multirate_copayment_preserves_all_documented_options() -> None:
    finding = _finding(
        "A 5%, 10%, 15%, or 20% co-payment applies if the Voluntary Co-payment option "
        "is selected and an inpatient claim is admitted."
    )

    assert finding.object_or_effect == (
        "one of 5%, 10%, 15%, or 20% of the admissible claim amount, "
        "depending on the documented selected co-payment option"
    )
    assert finding.trigger == (
        "if the Voluntary Co-payment option is selected and an inpatient claim is admitted"
    )
    assert finding.finding_status == "CONDITIONAL"
    assert finding.derivation_type == "CONDITIONAL_DERIVATION"


def test_multirate_reasoning_does_not_silently_choose_first_percentage() -> None:
    finding = _finding(
        "The insured bears 5%, 10%, 15%, or 20% of the eligible claim amount if the "
        "selected voluntary co-payment option applies."
    )

    assert finding.object_or_effect != "5% of the admissible claim amount"
    for rate in ("5%", "10%", "15%", "20%"):
        assert rate in finding.object_or_effect


def test_duplicate_percentage_mentions_do_not_create_duplicate_options() -> None:
    item = _evidence(
        "A 10% co-payment applies if the condition is met; the same 10% co-payment remains applicable."
    )
    item = replace(item, source_excerpt=item.claim)
    data = build_rule_input(
        requirement_id=item.requirement_id,
        evidence=(item,),
        approved_context={},
    )

    finding = conditional_copayment_obligation(data)[0]
    assert finding.object_or_effect == "10% of the admissible claim amount"
