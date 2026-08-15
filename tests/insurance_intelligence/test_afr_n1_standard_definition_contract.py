from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from insurance_intelligence.terminology.health_regulatory_definition_seed import (
    build_health_regulatory_definition_registry,
)
from insurance_intelligence.terminology.standard_definitions import (
    DefinitionEvidenceClass,
    DefinitionSourceReference,
    GovernedStandardDefinition,
    InsuranceCategory,
    StandardDefinitionError,
    StandardDefinitionRegistry,
)


def _definition(
    *,
    definition_id: str,
    concept_id: str,
    category: InsuranceCategory,
    version: str = "1.0",
    text: str = "Governed definition text.",
    effective_from: date = date(2024, 1, 1),
    effective_to: date | None = None,
    aliases: tuple[str, ...] = (),
    not_synonyms: tuple[str, ...] = (),
) -> GovernedStandardDefinition:
    return GovernedStandardDefinition(
        definition_id=definition_id,
        canonical_concept_id=concept_id,
        category=category,
        version=version,
        standard_definition=text,
        source=DefinitionSourceReference(
            source_id=f"source:{definition_id}",
            authority="IRDAI",
            locator="test clause",
            source_title="Test primary source",
        ),
        evidence_class=DefinitionEvidenceClass.PRIMARY_REGULATORY_SOURCE,
        effective_from=effective_from,
        effective_to=effective_to,
        aliases=aliases,
        not_synonyms=not_synonyms,
    )


def test_afr_n1_current_ped_resolution_rejects_stale_four_year_meaning() -> None:
    registry = build_health_regulatory_definition_registry()

    old = registry.resolve(
        category=InsuranceCategory.HEALTH,
        canonical_concept_id="health.definition.pre_existing_disease",
        as_of=date(2023, 1, 1),
    )
    current = registry.resolve(
        category=InsuranceCategory.HEALTH,
        canonical_concept_id="health.definition.pre_existing_disease",
        as_of=date(2026, 8, 15),
    )

    assert "48 months" in old.standard_definition
    assert old.version == "1.0"
    assert "36 months" in current.standard_definition
    assert "48 months" not in current.standard_definition
    assert "four years" not in current.standard_definition.casefold()
    assert current.version == "2.0"
    assert current.source.authority == "IRDAI"
    assert current.evidence_class is DefinitionEvidenceClass.PRIMARY_REGULATORY_SOURCE


def test_afr_n1_definition_lookup_is_as_of_not_timeless_latest() -> None:
    registry = build_health_regulatory_definition_registry()

    before = registry.resolve(
        category=InsuranceCategory.HEALTH,
        canonical_concept_id="health.definition.pre_existing_disease",
        as_of=date(2024, 3, 31),
    )
    after = registry.resolve(
        category=InsuranceCategory.HEALTH,
        canonical_concept_id="health.definition.pre_existing_disease",
        as_of=date(2024, 4, 1),
    )

    assert before.definition_id != after.definition_id
    assert before.effective_to == date(2024, 3, 31)
    assert after.effective_from == date(2024, 4, 1)


def test_afr_n1_reference_never_mutate_requires_new_version() -> None:
    registry = StandardDefinitionRegistry()
    original = _definition(
        definition_id="health.room_rent.v1",
        concept_id="health.definition.room_rent",
        category=InsuranceCategory.HEALTH,
        text="Room Rent includes associated medical expenses.",
    )
    registry.register(original)

    with pytest.raises(StandardDefinitionError, match="immutable"):
        registry.register(
            replace(
                original,
                standard_definition="Room Rent means only the room charge.",
            )
        )


def test_afr_n1_category_namespace_is_mandatory() -> None:
    with pytest.raises(StandardDefinitionError, match="namespaced"):
        _definition(
            definition_id="bad-health-ncb",
            concept_id="motor.definition.no_claim_bonus",
            category=InsuranceCategory.HEALTH,
        )


def test_afr_n1_motor_ncb_and_health_cumulative_bonus_can_never_share_identity() -> None:
    registry = StandardDefinitionRegistry()
    health = _definition(
        definition_id="health.cumulative_bonus.v1",
        concept_id="health.definition.cumulative_bonus",
        category=InsuranceCategory.HEALTH,
        text="Health cumulative bonus definition.",
        aliases=("no claim bonus", "NCB"),
    )
    motor = _definition(
        definition_id="motor.no_claim_bonus.v1",
        concept_id="motor.definition.no_claim_bonus",
        category=InsuranceCategory.MOTOR,
        text="Motor no claim bonus definition.",
        aliases=("no claim bonus", "NCB"),
    )
    registry.register(health)
    registry.register(motor)

    resolved_health = registry.resolve(
        category=InsuranceCategory.HEALTH,
        canonical_concept_id="health.definition.cumulative_bonus",
        as_of=date(2026, 1, 1),
    )
    resolved_motor = registry.resolve(
        category=InsuranceCategory.MOTOR,
        canonical_concept_id="motor.definition.no_claim_bonus",
        as_of=date(2026, 1, 1),
    )

    assert resolved_health.definition_id != resolved_motor.definition_id
    assert resolved_health.category is InsuranceCategory.HEALTH
    assert resolved_motor.category is InsuranceCategory.MOTOR


def test_afr_n1_overlapping_definition_versions_fail_closed() -> None:
    registry = StandardDefinitionRegistry()
    registry.register(
        _definition(
            definition_id="health.room_rent.v1",
            concept_id="health.definition.room_rent",
            category=InsuranceCategory.HEALTH,
            version="1.0",
            effective_from=date(2024, 1, 1),
            effective_to=date(2025, 12, 31),
        )
    )
    registry.register(
        _definition(
            definition_id="health.room_rent.v2",
            concept_id="health.definition.room_rent",
            category=InsuranceCategory.HEALTH,
            version="2.0",
            effective_from=date(2025, 1, 1),
        )
    )

    with pytest.raises(StandardDefinitionError, match="overlap"):
        registry.resolve(
            category=InsuranceCategory.HEALTH,
            canonical_concept_id="health.definition.room_rent",
            as_of=date(2025, 6, 1),
        )


def test_afr_n1_missing_applicable_definition_fails_closed() -> None:
    registry = StandardDefinitionRegistry()
    registry.register(
        _definition(
            definition_id="health.room_rent.v1",
            concept_id="health.definition.room_rent",
            category=InsuranceCategory.HEALTH,
            effective_from=date(2025, 1, 1),
        )
    )

    with pytest.raises(StandardDefinitionError, match="no governed standard definition"):
        registry.resolve(
            category=InsuranceCategory.HEALTH,
            canonical_concept_id="health.definition.room_rent",
            as_of=date(2024, 12, 31),
        )


def test_afr_n1_alias_and_false_friend_guard_cannot_overlap() -> None:
    with pytest.raises(StandardDefinitionError, match="must not overlap"):
        _definition(
            definition_id="health.restoration.v1",
            concept_id="health.definition.restoration",
            category=InsuranceCategory.HEALTH,
            aliases=("restoration", "recharge"),
            not_synonyms=("recharge",),
        )


def test_afr_n1_definition_contract_remains_separate_from_product_fact_and_applicability() -> None:
    fields = set(GovernedStandardDefinition.__dataclass_fields__)
    forbidden = {
        "product_reference",
        "insurer_id",
        "product_id",
        "sum_insured",
        "policy_variant",
        "zone",
        "customer_context",
        "recommendation",
        "comparison_value",
    }

    assert forbidden.isdisjoint(fields)
    assert {
        "canonical_concept_id",
        "category",
        "version",
        "standard_definition",
        "source",
        "evidence_class",
        "effective_from",
        "effective_to",
        "aliases",
        "not_synonyms",
    } <= fields
