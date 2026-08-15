from __future__ import annotations

from datetime import date

import pytest

from insurance_intelligence.terminology.health_regulatory_definition_seed import (
    build_health_regulatory_definition_registry,
)
from insurance_intelligence.terminology.motor_regulatory_definition_seed import (
    build_motor_regulatory_definition_registry,
)
from insurance_intelligence.terminology.standard_definitions import (
    DefinitionEvidenceClass,
    InsuranceCategory,
    StandardDefinitionError,
    StandardDefinitionRegistry,
)


AS_OF = date(2026, 8, 15)


def _combined_registry() -> StandardDefinitionRegistry:
    combined = StandardDefinitionRegistry()
    for definition in build_health_regulatory_definition_registry().all():
        combined.register(definition)
    for definition in build_motor_regulatory_definition_registry().all():
        combined.register(definition)
    return combined


def test_afr_n1c_current_health_cumulative_bonus_preserves_sum_insured_meaning() -> None:
    definition = build_health_regulatory_definition_registry().resolve(
        category=InsuranceCategory.HEALTH,
        canonical_concept_id="health.definition.cumulative_bonus",
        as_of=AS_OF,
    )

    assert definition.category is InsuranceCategory.HEALTH
    assert definition.source.authority == "IRDAI"
    assert (
        definition.evidence_class
        is DefinitionEvidenceClass.PRIMARY_REGULATOR_GUIDANCE_SOURCE
    )
    assert "Sum Insured" in definition.standard_definition
    assert "without an associated increase in premium" in definition.standard_definition


def test_afr_n1c_current_motor_ncb_is_a_distinct_motor_identity() -> None:
    definition = build_motor_regulatory_definition_registry().resolve(
        category=InsuranceCategory.MOTOR,
        canonical_concept_id="motor.definition.no_claim_bonus",
        as_of=AS_OF,
    )

    assert definition.category is InsuranceCategory.MOTOR
    assert definition.source.authority == "IRDAI"
    assert (
        definition.evidence_class
        is DefinitionEvidenceClass.PRIMARY_REGULATOR_GUIDANCE_SOURCE
    )
    assert "No Claim Bonus (NCB)" in definition.standard_definition
    assert "NIL claims" in definition.standard_definition
    assert "Own Damage premium" in definition.source.locator


def test_afr_n1c_alias_resolution_requires_category_and_keeps_concepts_separate() -> None:
    combined = _combined_registry()

    health = combined.resolve_alias(
        category=InsuranceCategory.HEALTH,
        alias="  CUMULATIVE   BONUS ",
        as_of=AS_OF,
    )
    motor = combined.resolve_alias(
        category=InsuranceCategory.MOTOR,
        alias="ncb",
        as_of=AS_OF,
    )

    assert health.canonical_concept_id == "health.definition.cumulative_bonus"
    assert motor.canonical_concept_id == "motor.definition.no_claim_bonus"
    assert health.definition_id != motor.definition_id


def test_afr_n1c_health_ncb_is_not_silently_collapsed_to_cumulative_bonus() -> None:
    combined = _combined_registry()

    with pytest.raises(StandardDefinitionError, match="category/alias/as_of"):
        combined.resolve_alias(
            category=InsuranceCategory.HEALTH,
            alias="NCB",
            as_of=AS_OF,
        )


def test_afr_n1c_motor_cumulative_bonus_is_not_silently_mapped_to_motor_ncb() -> None:
    combined = _combined_registry()

    with pytest.raises(StandardDefinitionError, match="category/alias/as_of"):
        combined.resolve_alias(
            category=InsuranceCategory.MOTOR,
            alias="cumulative bonus",
            as_of=AS_OF,
        )


def test_afr_n1c_cross_category_concept_lookup_fails_closed() -> None:
    combined = _combined_registry()

    with pytest.raises(StandardDefinitionError, match="category/concept/as_of"):
        combined.resolve(
            category=InsuranceCategory.HEALTH,
            canonical_concept_id="motor.definition.no_claim_bonus",
            as_of=AS_OF,
        )

    with pytest.raises(StandardDefinitionError, match="category/concept/as_of"):
        combined.resolve(
            category=InsuranceCategory.MOTOR,
            canonical_concept_id="health.definition.cumulative_bonus",
            as_of=AS_OF,
        )
