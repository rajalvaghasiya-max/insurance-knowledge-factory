from __future__ import annotations

from datetime import date

import pytest

from insurance_intelligence.terminology.health_regulatory_definition_seed import (
    build_health_regulatory_definition_registry,
)
from insurance_intelligence.terminology.standard_definitions import (
    DefinitionEvidenceClass,
    InsuranceCategory,
    StandardDefinitionError,
)


def test_afr_n1b_historical_room_rent_preserves_associated_medical_expense_consequence() -> None:
    registry = build_health_regulatory_definition_registry()

    definition = registry.resolve(
        category=InsuranceCategory.HEALTH,
        canonical_concept_id="health.definition.room_rent",
        as_of=date(2023, 1, 1),
    )

    normalized = definition.standard_definition.casefold()
    assert "room and boarding expenses" in normalized
    assert "shall include the associated medical expenses" in normalized
    assert definition.version == "1.0"
    assert definition.source.authority == "IRDAI"
    assert definition.source.source_id == "IRDAI/HLT/REG/CIR/193/07/2020"
    assert definition.evidence_class is DefinitionEvidenceClass.PRIMARY_REGULATORY_SOURCE


def test_afr_n1b_room_rent_does_not_collapse_to_room_charge_only() -> None:
    registry = build_health_regulatory_definition_registry()

    definition = registry.resolve(
        category=InsuranceCategory.HEALTH,
        canonical_concept_id="health.definition.room_rent",
        as_of=date(2023, 6, 30),
    )

    assert definition.standard_definition != "Room Rent means only the room charge."
    assert "associated medical expenses" in definition.standard_definition.casefold()


def test_afr_n1b_current_room_rent_fails_closed_until_current_primary_source_is_pinned() -> None:
    registry = build_health_regulatory_definition_registry()

    with pytest.raises(StandardDefinitionError, match="no governed standard definition"):
        registry.resolve(
            category=InsuranceCategory.HEALTH,
            canonical_concept_id="health.definition.room_rent",
            as_of=date(2026, 8, 15),
        )
