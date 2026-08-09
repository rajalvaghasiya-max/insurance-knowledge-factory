from dataclasses import replace

import pytest

from insurance_intelligence.contracts.evidence import EvidencePackage, Lineage
from insurance_intelligence.reasoning.rules import (
    ReasoningRuleError,
    build_rule_input,
    conditional_copayment_obligation,
)


FULL_PAGE_TEXT = (
    "A 10% co-payment applies where the insured person's age at entry is 61 years or above. "
    "The co-payment does not apply where the insured person entered before age 61 and renewed continuously. "
    "The policy wording limits this co-payment to Sections II.1 and II.25."
)


def _evidence(*, claim: str, source_excerpt: str | None) -> EvidencePackage:
    return EvidencePackage(
        evidence_id="ev-empty-reviewed-claim",
        requirement_id="req-empty-reviewed-claim",
        subject_reference="Star Comprehensive",
        governed_entity_reference="star_health:star_comprehensive",
        field_or_topic="conditional_copayment",
        claim=claim,
        evidence_role="SUPPORTING",
        source_type="POLICY_WORDING",
        document_reference="star-policy-wording",
        document_version="v1",
        effective_from=None,
        effective_to=None,
        page=39,
        section="Conditional co-payment",
        source_excerpt=source_excerpt,
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


def test_empty_reviewed_claim_does_not_fall_back_to_page_excerpt():
    item = _evidence(claim="", source_excerpt=FULL_PAGE_TEXT)
    data = build_rule_input(
        requirement_id="req-empty-reviewed-claim",
        evidence=(item,),
        approved_context={},
    )

    with pytest.raises(ReasoningRuleError, match="non-empty reviewed claim"):
        conditional_copayment_obligation(data)


def test_nonempty_reviewed_claim_retains_existing_reasoning_path():
    item = _evidence(claim=FULL_PAGE_TEXT, source_excerpt=FULL_PAGE_TEXT)
    data = build_rule_input(
        requirement_id="req-empty-reviewed-claim",
        evidence=(item,),
        approved_context={},
    )

    finding = conditional_copayment_obligation(data)[0]
    assert finding.object_or_effect == "10% of the admissible claim amount"
    assert "61 years or above" in finding.trigger
    assert finding.exception is not None
    assert finding.applicability_scope is not None
