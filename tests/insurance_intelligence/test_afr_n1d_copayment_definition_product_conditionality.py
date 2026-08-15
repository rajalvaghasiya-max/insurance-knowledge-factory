from __future__ import annotations

from datetime import date

import pytest

from insurance_intelligence.rule_certification.star_health import (
    STAR_COMPREHENSIVE_COPAYMENT_REVIEWED_STATEMENT,
    extract_star_comprehensive_conditional_copayment_finding,
)
from insurance_intelligence.terminology.health_regulatory_definition_seed import (
    build_health_regulatory_definition_registry,
)
from insurance_intelligence.terminology.standard_definitions import (
    DefinitionEvidenceClass,
    GovernedStandardDefinition,
    InsuranceCategory,
    StandardDefinitionError,
)


def _current_copayment():
    registry = build_health_regulatory_definition_registry()
    return registry.resolve(
        category=InsuranceCategory.HEALTH,
        canonical_concept_id="health.definition.copayment",
        as_of=date(2026, 8, 15),
    )


def test_afr_n1d_current_copayment_definition_preserves_cost_sharing_structure() -> None:
    definition = _current_copayment()
    text = definition.standard_definition.casefold()

    assert "specified amount / percentage" in text
    assert "admissible claim amount" in text
    assert "policyholder / insured" in text
    assert definition.source.authority == "IRDAI"
    assert definition.evidence_class is DefinitionEvidenceClass.PRIMARY_REGULATOR_GUIDANCE_SOURCE


def test_afr_n1d_copayment_aliases_resolve_only_inside_health_category() -> None:
    registry = build_health_regulatory_definition_registry()

    for alias in ("co-payment", "copayment", "co payment"):
        resolved = registry.resolve_alias(
            category=InsuranceCategory.HEALTH,
            alias=alias,
            as_of=date(2026, 8, 15),
        )
        assert resolved.canonical_concept_id == "health.definition.copayment"

    with pytest.raises(StandardDefinitionError, match="no governed standard definition"):
        registry.resolve_alias(
            category=InsuranceCategory.MOTOR,
            alias="copayment",
            as_of=date(2026, 8, 15),
        )


def test_afr_n1d_standard_definition_cannot_encode_star_specific_copayment_terms() -> None:
    definition = _current_copayment()
    text = definition.standard_definition.casefold()

    for product_specific_term in (
        "10%",
        "61 years",
        "age at entry",
        "renewed continuously",
        "section ii.1",
        "section ii.25",
        "star comprehensive",
    ):
        assert product_specific_term not in text


def test_afr_n1d_star_product_binding_supplies_value_trigger_exception_and_scope() -> None:
    finding = extract_star_comprehensive_conditional_copayment_finding()

    assert finding.object_or_effect == "10% of the admissible claim amount"
    assert finding.trigger == "where the insured person's age at entry is 61 years or above"
    assert "entered the policy before attaining 61 years" in (finding.exception or "")
    assert "renewed continuously without a break" in (finding.exception or "")
    assert "Sections II.1" in (finding.applicability_scope or "")
    assert "II.25" in (finding.applicability_scope or "")


def test_afr_n1d_definition_and_product_binding_are_complementary_not_substitutable() -> None:
    definition = _current_copayment()
    finding = extract_star_comprehensive_conditional_copayment_finding()

    assert "admissible claim amount" in definition.standard_definition.casefold()
    assert "10%" not in definition.standard_definition
    assert "10%" in finding.object_or_effect
    assert "61 years" not in definition.standard_definition
    assert "61 years" in (finding.trigger or "")


def test_afr_n1d_standard_definition_contract_has_no_product_applicability_fields() -> None:
    fields = set(GovernedStandardDefinition.__dataclass_fields__)
    forbidden = {
        "product_id",
        "product_reference",
        "insurer_id",
        "trigger",
        "exception",
        "applicability_scope",
        "obligation_value",
        "customer_context",
        "claim_outcome",
    }

    assert forbidden.isdisjoint(fields)
    assert "10% co-payment" in STAR_COMPREHENSIVE_COPAYMENT_REVIEWED_STATEMENT
