from __future__ import annotations

import json
from pathlib import Path

from insurance_intelligence.concepts.waiting_periods.policy import (
    WaitingPeriodSemanticEffect,
    waiting_period_concept_policy_v2,
)
from insurance_intelligence.generic_knowledge.contracts import (
    AccountingState,
    NormativeUnitKind,
    RelationshipType,
)


G2_PATH = Path(
    "docs/architecture/AR_3_0_G2_STAR_COMPREHENSIVE_DELIVERY_NEWBORN_ATOMIC_MAPPING.json"
)
G3_PATH = Path(
    "docs/architecture/AR_3_0_G3_STAR_COMPREHENSIVE_DELIVERY_NEWBORN_GENERIC_FAMILY_MAPPING.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_g3_accounts_for_every_g2_atomic_unit_exactly_once() -> None:
    g2 = _load(G2_PATH)
    g3 = _load(G3_PATH)

    g2_ids = [unit["unit_id"] for unit in g2["atomic_normative_units"]]
    mapped_ids = [mapping["unit_id"] for mapping in g3["generic_mappings"]]

    assert len(g2_ids) == 11
    assert len(mapped_ids) == 11
    assert len(mapped_ids) == len(set(mapped_ids))
    assert set(mapped_ids) == set(g2_ids)
    assert g3["architecture_pressure_result"]["all_atomic_units_family_accounted"] is True


def test_g3_uses_only_existing_generic_contract_enum_values() -> None:
    g3 = _load(G3_PATH)

    allowed_kinds = {item.value for item in NormativeUnitKind}
    allowed_relationships = {item.value for item in RelationshipType}
    allowed_accounting_states = {item.value for item in AccountingState}

    for mapping in g3["generic_mappings"]:
        assert mapping["normative_kind"] in allowed_kinds
        assert mapping["accounting_state"] in allowed_accounting_states
        if "relationship_type" in mapping:
            assert mapping["relationship_type"] in allowed_relationships


def test_waiting_period_units_fit_existing_waiting_period_policy_without_star_logic() -> None:
    g3 = _load(G3_PATH)
    policy = waiting_period_concept_policy_v2()
    policy_effects = {effect.value for effect in policy.semantic_effects}
    policy_relationships = {relationship.value for relationship in policy.allowed_relationship_types}

    waiting_mappings = {
        mapping["unit_id"]: mapping
        for mapping in g3["generic_mappings"]
        if mapping["generic_family"] == "waiting_periods"
    }

    assert set(waiting_mappings) == {
        "G2-DNB-04",
        "G2-DNB-05",
        "G2-DNB-06",
        "G2-DNB-07",
        "G2-DNB-08",
    }
    assert waiting_mappings["G2-DNB-04"]["waiting_period_effect"] == (
        WaitingPeriodSemanticEffect.DURATION.value
    )
    assert waiting_mappings["G2-DNB-05"]["waiting_period_effect"] == (
        WaitingPeriodSemanticEffect.START_BASIS.value
    )
    assert waiting_mappings["G2-DNB-06"]["waiting_period_effect"] == (
        WaitingPeriodSemanticEffect.CONTINUITY.value
    )

    for mapping in waiting_mappings.values():
        assert mapping["waiting_period_effect"] in policy_effects
        if "relationship_type" in mapping:
            assert mapping["relationship_type"] in policy_relationships

    assert waiting_mappings["G2-DNB-07"]["relationship_type"] == "APPLIES_WHEN"
    assert waiting_mappings["G2-DNB-08"]["relationship_type"] == "MODIFIES"
    assert g3["architecture_pressure_result"]["new_waiting_period_effect_required"] is False
    assert g3["architecture_pressure_result"]["star_specific_runtime_logic_required"] is False


def test_limit_families_are_representable_but_values_remain_deferred() -> None:
    g3 = _load(G3_PATH)
    mappings = {mapping["unit_id"]: mapping for mapping in g3["generic_mappings"]}

    for unit_id in ("G2-DNB-02", "G2-DNB-03"):
        mapping = mappings[unit_id]
        assert mapping["generic_family"] == "benefit_limits"
        assert mapping["relationship_type"] == RelationshipType.LIMITED_BY.value
        assert mapping["accounting_state"] == AccountingState.DEFERRED_WITH_REASON.value
        assert "Exact" in mapping["deferred_reason"]

    assert g3["architecture_pressure_result"]["publication_ready"] is False
    assert g3["architecture_pressure_result"]["comparison_ready"] is False


def test_g3_preserves_every_material_g2_residue_and_its_blockers() -> None:
    g2 = _load(G2_PATH)
    g3 = _load(G3_PATH)

    g2_residue = {item["residue_id"]: item for item in g2["residue"]}
    g3_residue = {item["residue_id"]: item for item in g3["inherited_material_residue"]}

    assert set(g3_residue) == set(g2_residue) == {
        "G2-DNB-X01",
        "G2-DNB-X02",
        "G2-DNB-X03",
    }
    for residue_id, item in g3_residue.items():
        assert item["material"] is True
        assert item["accounting_state"] == AccountingState.DEFERRED_WITH_REASON.value
        assert set(item["blocks"]) == set(g2_residue[residue_id]["blocks"])
        assert "COMPARISON_READINESS" in item["blocks"]


def test_g3_does_not_confuse_representability_with_governed_truth() -> None:
    g3 = _load(G3_PATH)

    assert g3["status"] == "GENERIC_MAPPING_PROPOSED_NOT_BOUND"
    result = g3["architecture_pressure_result"]
    assert result["new_generic_contract_required"] is False
    assert result["star_specific_runtime_logic_required"] is False
    assert result["publication_ready"] is False
    assert result["comparison_ready"] is False

    guardrails = " ".join(g3["guardrails"]).casefold()
    assert "mapped means representable" in guardrails
    assert "not published" in guardrails
    assert "material g2 residue" in guardrails
    assert "reset trigger and reset effect must remain separate" in guardrails
    assert "no insurer or product identifier" in guardrails
