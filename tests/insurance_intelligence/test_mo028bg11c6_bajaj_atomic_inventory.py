from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ATOMIC_PATH = ROOT / "docs" / "architecture" / "MO_028B_G11_C6_BAJAJ_ATOMIC_WAITING_PERIOD_INVENTORY.json"
ORIGINAL_PATH = ROOT / "docs" / "architecture" / "MO_028B_G11_BAJAJ_MY_HEALTH_CARE_NORMATIVE_INVENTORY.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_atomic_inventory_preserves_original_thirteen_clause_groups() -> None:
    artifact = _load(ATOMIC_PATH)
    original = _load(ORIGINAL_PATH)

    groups = artifact["clause_groups"]
    assert len(groups) == 13
    assert len({group["group_id"] for group in groups}) == 13
    assert {group["original_unit_id"] for group in groups} == {
        unit["unit_id"] for unit in original["normative_units"]
    }


def test_every_clause_group_has_at_least_one_atomic_unit() -> None:
    artifact = _load(ATOMIC_PATH)
    counts: dict[str, int] = defaultdict(int)
    for unit in artifact["atomic_units"]:
        counts[unit["parent_clause_group_id"]] += 1

    for group in artifact["clause_groups"]:
        assert counts[group["group_id"]] >= 1


def test_atomic_inventory_has_expected_source_expression_granularity() -> None:
    artifact = _load(ATOMIC_PATH)
    units = artifact["atomic_units"]
    assert len(units) == 27
    assert len({unit["atomic_unit_id"] for unit in units}) == 27

    expected = {
        "bajaj_mhc_ped_duration_selection_domain",
        "bajaj_mhc_ped_si_enhancement_reapplication",
        "bajaj_mhc_ped_portability_credit",
        "bajaj_mhc_specific_duration_selection_domain",
        "bajaj_mhc_specific_si_enhancement_reapplication",
        "bajaj_mhc_specific_longer_of_ped_relationship",
        "bajaj_mhc_specific_portability_credit",
        "bajaj_mhc_investigation_initial_wait",
        "bajaj_mhc_investigation_ped_application",
        "bajaj_mhc_maternity_upfront_premium_reduction",
        "bajaj_mhc_baby_care_upfront_premium_reduction",
        "bajaj_mhc_portability_continuity_general",
        "bajaj_mhc_migration_continuity_general",
        "bajaj_mhc_si_enhancement_reset_general",
        "bajaj_mhc_new_member_reset",
        "bajaj_mhc_cataract_waiting_period_dependency",
        "bajaj_mhc_daycare_inherits_standard_waits",
    }
    assert expected <= {unit["atomic_unit_id"] for unit in units}


def test_every_atomic_unit_has_confirmed_source_sufficiency() -> None:
    artifact = _load(ATOMIC_PATH)
    for unit in artifact["atomic_units"]:
        assert unit["source_sufficiency_review"] == "CONFIRMED"
        assert unit["source_pages"]
        assert unit["source_locator"].strip()
        assert unit["source_line_range"].strip()
        assert unit["source_support_summary"].strip()
        assert unit["normative_proposition"].strip()
        assert unit["material_effects"]


def test_no_original_material_effect_disappears_during_atomicization() -> None:
    artifact = _load(ATOMIC_PATH)
    effects_by_group: dict[str, set[str]] = defaultdict(set)
    for unit in artifact["atomic_units"]:
        effects_by_group[unit["parent_clause_group_id"]].update(unit["material_effects"])

    for group in artifact["clause_groups"]:
        assert set(group["original_material_effects"]) <= effects_by_group[group["group_id"]]


def test_atomic_units_do_not_pre_author_accounting_or_mapping_outcomes() -> None:
    artifact = _load(ATOMIC_PATH)
    forbidden = {
        "accounting_state",
        "semantic_fact_ids",
        "relationship_fact_ids",
        "mapping_kind",
        "publication_status",
    }
    for unit in artifact["atomic_units"]:
        assert forbidden.isdisjoint(unit)


def test_generic_si_enhancement_clause_is_not_ontology_duplicated() -> None:
    artifact = _load(ATOMIC_PATH)
    generic = [
        unit
        for unit in artifact["atomic_units"]
        if unit["parent_clause_group_id"] == "cg_si_enhancement"
    ]
    assert [unit["atomic_unit_id"] for unit in generic] == [
        "bajaj_mhc_si_enhancement_reset_general"
    ]
    assert set(generic[0]["material_effects"]) == {
        "SUM_INSURED_ENHANCEMENT",
        "START_BASIS",
        "APPLICABILITY",
    }


def test_relationship_propositions_remain_atomic_and_distinct() -> None:
    artifact = _load(ATOMIC_PATH)
    units = {unit["atomic_unit_id"]: unit for unit in artifact["atomic_units"]}

    assert units["bajaj_mhc_specific_longer_of_ped_relationship"]["material_effects"] == [
        "CROSS_CONCEPT_RELATIONSHIP",
        "APPLICABILITY",
    ]
    assert "CROSS_CONCEPT_RELATIONSHIP" in units[
        "bajaj_mhc_cataract_waiting_period_dependency"
    ]["material_effects"]
    assert "CROSS_CONCEPT_RELATIONSHIP" in units[
        "bajaj_mhc_daycare_inherits_standard_waits"
    ]["material_effects"]


def test_migration_units_preserve_c5_fail_closed_governance_note() -> None:
    artifact = _load(ATOMIC_PATH)
    migration = [
        unit
        for unit in artifact["atomic_units"]
        if unit["parent_clause_group_id"] == "cg_migration"
    ]
    assert len(migration) == 2
    for unit in migration:
        assert "BENEFIT_ESTABLISHING" in unit["governance_note"]
        assert "unquantified" in unit["governance_note"].lower()


def test_c6_atomicization_does_not_widen_runtime_contract_or_allow_mixed_accounting() -> None:
    decision = _load(ATOMIC_PATH)["review_decision"]
    assert decision["atomic_inventory_ready_for_mapping"] is True
    assert decision["mixed_accounting_allowed"] is False
    assert decision["runtime_normative_unit_contract_changed"] is False
    assert decision["automatic_segmentation_used"] is False
