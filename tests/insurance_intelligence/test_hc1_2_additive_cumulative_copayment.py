from insurance_intelligence.benefits.copayment_composition import (
    CopaymentCompositionType,
    resolve_copayment_composition,
)
from insurance_intelligence.contracts.evidence import EvidencePackage, Lineage
from insurance_intelligence.reasoning.rules import (
    build_rule_input,
    conditional_copayment_obligation,
)


PAGE_44_REVIEWED = (
    "If prolonged hospitalization is not intimated within the documented notification period, "
    "an additional cumulative 10% co-payment applies. This co-payment is applicable only to "
    "the prolonged-hospitalization notification failure described by the policy wording."
)
PAGE_45_REVIEWED = (
    "If the specified non-network organ-transplant process requirements are not followed, "
    "an additional 20% co-payment applies. This co-payment is applicable only to the documented "
    "non-network organ-transplant process failure."
)
BAJAJ_EXISTING = (
    "For International Cover - Emergency Care only, a mandatory 10% co-payment applies and is "
    "additional to any other co-payment or deductible applicable under the policy."
)


def _evidence(statement: str, *, candidate: str, page: int) -> EvidencePackage:
    return EvidencePackage(
        evidence_id=f"ev-{candidate}",
        requirement_id=f"req-{candidate}",
        subject_reference="product:niva_bupa:reassure_3_0",
        governed_entity_reference=f"assertion:{candidate}",
        field_or_topic="conditional_copayment",
        claim=statement,
        evidence_role="DEFINING",
        source_type="POLICY_WORDING",
        document_reference="niva_bupa_reassure_3_0_policy_wording_v1",
        document_version="niva_bupa_reassure_3_0_policy_wording_v1",
        effective_from=None,
        effective_to=None,
        page=page,
        section="Conditional co-payment",
        source_excerpt=statement,
        normalized_fact_reference=f"reassure-3:{candidate}",
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
        retrieval_basis=("reviewed_binding", candidate),
        confidence=1.0,
    )


def _finding(statement: str, *, candidate: str, page: int):
    evidence = _evidence(statement, candidate=candidate, page=page)
    return conditional_copayment_obligation(
        build_rule_input(
            requirement_id=evidence.requirement_id,
            evidence=(evidence,),
            approved_context={},
            scope="niva_bupa:reassure_3_0",
        )
    )[0]


def test_composition_contract_distinguishes_cumulative_additive_and_standalone() -> None:
    cumulative = resolve_copayment_composition(PAGE_44_REVIEWED)
    additive = resolve_copayment_composition(PAGE_45_REVIEWED)
    standalone = resolve_copayment_composition(
        "If treatment occurs outside the network, a 20% co-payment applies."
    )

    assert cumulative.composition_type is CopaymentCompositionType.CUMULATIVE
    assert cumulative.source_phrase == "additional cumulative 10% co-payment"
    assert cumulative.stacks_with_other_cost_sharing is True

    assert additive.composition_type is CopaymentCompositionType.ADDITIVE
    assert additive.source_phrase == "additional 20% co-payment"
    assert additive.stacks_with_other_cost_sharing is True

    assert standalone.composition_type is CopaymentCompositionType.STANDALONE
    assert standalone.source_phrase is None
    assert standalone.stacks_with_other_cost_sharing is False


def test_page_44_cumulative_modifier_is_preserved_in_production_reasoning() -> None:
    finding = _finding(PAGE_44_REVIEWED, candidate="candidate_page_44", page=44)

    assert finding.object_or_effect == (
        "10% of the admissible claim amount; additional cumulative 10% co-payment"
    )
    assert finding.trigger == (
        "If prolonged hospitalization is not intimated within the documented notification period"
    )
    assert finding.applicability_scope == (
        "This co-payment is applicable only to the prolonged-hospitalization notification failure described by the policy wording"
    )


def test_page_45_additional_modifier_is_preserved_in_production_reasoning() -> None:
    finding = _finding(PAGE_45_REVIEWED, candidate="candidate_page_45", page=45)

    assert finding.object_or_effect == (
        "20% of the admissible claim amount; additional 20% co-payment"
    )
    assert finding.trigger == (
        "If the specified non-network organ-transplant process requirements are not followed"
    )
    assert finding.applicability_scope == (
        "This co-payment is applicable only to the documented non-network organ-transplant process failure"
    )


def test_preexisting_explicit_other_cost_share_form_remains_preserved() -> None:
    composition = resolve_copayment_composition(BAJAJ_EXISTING)

    assert composition.composition_type is CopaymentCompositionType.ADDITIVE
    assert composition.source_phrase == (
        "additional to any other co-payment or deductible applicable under the policy"
    )
    assert composition.stacks_with_other_cost_sharing is True
