from datetime import date

import pytest

from insurance_intelligence.benefits.contracts import PublicationStatus, ReviewStatus
from insurance_intelligence.decision_support.circumstance_relevance import (
    CircumstanceOperator,
    CircumstanceRelevanceError,
    CircumstanceRelevanceRule,
    CustomerCircumstanceFact,
    CustomerFactProvenance,
    RelevanceClaimType,
    RelevanceEffect,
    RelevanceRuleBasis,
    evaluate_circumstance_relevance,
)


AS_OF = date(2026, 8, 9)


def star_entry_age_rule() -> CircumstanceRelevanceRule:
    return CircumstanceRelevanceRule(
        rule_id="circumstance_rule:star_comprehensive:copayment:entry_age_61_plus:v1",
        rule_version="1.0",
        circumstance_id="insured_entry_age_years",
        operator=CircumstanceOperator.GREATER_THAN_OR_EQUAL,
        expected_value=61,
        target_dimension_id="copayment",
        claim_type=RelevanceClaimType.PRODUCT_APPLICABILITY,
        effect=RelevanceEffect.CONDITION_POTENTIALLY_APPLICABLE,
        basis=RelevanceRuleBasis.PRODUCT_POLICY_MECHANIC,
        rationale=(
            "The governed Star Comprehensive conditional-copayment mechanic is triggered "
            "where insured entry age is 61 years or above, subject to its governed exception and scope."
        ),
        evidence_reference_ids=(
            "ev_star_comprehensive_conditional_copayment_policy_wording",
        ),
        review_status=ReviewStatus.APPROVED,
        publication_status=PublicationStatus.PUBLISHED,
        effective_from=date(2026, 1, 1),
    )


def fact(*, value: object, provenance: CustomerFactProvenance) -> CustomerCircumstanceFact:
    return CustomerCircumstanceFact(
        fact_id=f"customer_fact:insured_entry_age:{value}",
        subject_reference="customer_subject:mother",
        circumstance_id="insured_entry_age_years",
        value=value,
        provenance=provenance,
        raw_statement=f"Entry age is {value} years.",
    )


def test_declared_fact_can_drive_governed_product_applicability() -> None:
    result = evaluate_circumstance_relevance(
        fact=fact(value=67, provenance=CustomerFactProvenance.DECLARED),
        rule=star_entry_age_rule(),
        as_of=AS_OF,
    )

    assert result is not None
    assert result.target_dimension_id == "copayment"
    assert result.claim_type is RelevanceClaimType.PRODUCT_APPLICABILITY
    assert result.effect is RelevanceEffect.CONDITION_POTENTIALLY_APPLICABLE
    assert result.rule_version == "1.0"
    assert result.evidence_reference_ids == (
        "ev_star_comprehensive_conditional_copayment_policy_wording",
    )


def test_non_matching_circumstance_returns_no_finding_not_advice() -> None:
    result = evaluate_circumstance_relevance(
        fact=fact(value=35, provenance=CustomerFactProvenance.DECLARED),
        rule=star_entry_age_rule(),
        as_of=AS_OF,
    )
    assert result is None


def test_inferred_fact_must_be_confirmed_before_deterministic_use() -> None:
    with pytest.raises(CircumstanceRelevanceError, match="must be confirmed"):
        evaluate_circumstance_relevance(
            fact=fact(value=67, provenance=CustomerFactProvenance.INFERRED),
            rule=star_entry_age_rule(),
            as_of=AS_OF,
        )


def test_needs_analysis_rule_is_rejected_from_default_path() -> None:
    with pytest.raises(CircumstanceRelevanceError, match="outside the default MO-027D path"):
        CircumstanceRelevanceRule(
            rule_id="invalid:needs-analysis",
            rule_version="1.0",
            circumstance_id="age_years",
            operator=CircumstanceOperator.GREATER_THAN_OR_EQUAL,
            expected_value=65,
            target_dimension_id="copayment",
            claim_type=RelevanceClaimType.NEEDS_ANALYSIS,
            effect=RelevanceEffect.DIMENSION_MATERIALLY_APPLICABLE,
            basis=RelevanceRuleBasis.GOVERNED_DOMAIN_EVIDENCE,
            rationale="Older customers should care more about copayment.",
            evidence_reference_ids=("evidence:domain",),
            review_status=ReviewStatus.APPROVED,
            publication_status=PublicationStatus.PUBLISHED,
            effective_from=AS_OF,
        )


def test_unpublished_rule_cannot_drive_customer_relevance() -> None:
    base = star_entry_age_rule()
    unpublished = CircumstanceRelevanceRule(
        rule_id=base.rule_id,
        rule_version=base.rule_version,
        circumstance_id=base.circumstance_id,
        operator=base.operator,
        expected_value=base.expected_value,
        target_dimension_id=base.target_dimension_id,
        claim_type=base.claim_type,
        effect=base.effect,
        basis=base.basis,
        rationale=base.rationale,
        evidence_reference_ids=base.evidence_reference_ids,
        review_status=ReviewStatus.APPROVED,
        publication_status=PublicationStatus.DRAFT,
        effective_from=base.effective_from,
    )
    with pytest.raises(CircumstanceRelevanceError, match="approved and published"):
        evaluate_circumstance_relevance(
            fact=fact(value=67, provenance=CustomerFactProvenance.DECLARED),
            rule=unpublished,
            as_of=AS_OF,
        )


def test_rule_requires_evidence_lineage() -> None:
    with pytest.raises(CircumstanceRelevanceError, match="must not be empty"):
        CircumstanceRelevanceRule(
            rule_id="invalid:no-evidence",
            rule_version="1.0",
            circumstance_id="insured_entry_age_years",
            operator=CircumstanceOperator.GREATER_THAN_OR_EQUAL,
            expected_value=61,
            target_dimension_id="copayment",
            claim_type=RelevanceClaimType.PRODUCT_APPLICABILITY,
            effect=RelevanceEffect.CONDITION_POTENTIALLY_APPLICABLE,
            basis=RelevanceRuleBasis.PRODUCT_POLICY_MECHANIC,
            rationale="Governed applicability rule.",
            evidence_reference_ids=(),
            review_status=ReviewStatus.APPROVED,
            publication_status=PublicationStatus.PUBLISHED,
            effective_from=AS_OF,
        )


def test_rule_is_effective_date_bound() -> None:
    with pytest.raises(CircumstanceRelevanceError, match="not active"):
        evaluate_circumstance_relevance(
            fact=fact(value=67, provenance=CustomerFactProvenance.CONFIRMED),
            rule=star_entry_age_rule(),
            as_of=date(2025, 12, 31),
        )


def test_default_contract_has_no_priority_weight_or_recommendation_fields() -> None:
    forbidden = {
        "priority_weight",
        "weight",
        "score",
        "overall_score",
        "winner",
        "recommendation",
        "suitability",
        "should_prioritize",
    }
    assert forbidden.isdisjoint(CircumstanceRelevanceRule.__dataclass_fields__)
    assert forbidden.isdisjoint(CustomerCircumstanceFact.__dataclass_fields__)
