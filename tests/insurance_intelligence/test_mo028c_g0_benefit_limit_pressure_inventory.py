from __future__ import annotations

import json
from pathlib import Path


SELECTION = Path(
    "docs/architecture/MO_028C_G0_HEALTH_BENEFIT_LIMIT_PRESSURE_SELECTION.json"
)
INVENTORY = Path(
    "docs/architecture/MO_028C_G0_STAR_AROGYA_SANJEEVANI_BENEFIT_LIMIT_NORMATIVE_INVENTORY.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_g0_pressure_selection_has_three_distinct_semantic_roles() -> None:
    record = _load(SELECTION)
    products = record["selected_products"]
    assert len(products) == 3
    assert {item["selection_role"] for item in products} == {
        "FIRST_DETAILED_INVENTORY_AND_ADVERSARIAL_COMPOSITION_ANCHOR",
        "SECOND_PRODUCT_FIXED_AND_NESTED_AGGREGATE_PRESSURE",
        "THIRD_PRODUCT_NO_SUBLIMIT_AND_UP_TO_SUM_INSURED_PRESSURE",
    }
    assert record["g0_scope_decisions"]["cost_sharing_interaction_required_for_comparison_safety"] is True
    assert record["g0_scope_decisions"]["benefit_concept_identity_required_before_cross_product_comparison"] is True
    assert record["g0_scope_decisions"]["fuzzy_benefit_matching_allowed"] is False


def test_arogya_inventory_is_source_sufficient_and_unmapped() -> None:
    record = _load(INVENTORY)
    units = record["atomic_units"]
    summary = record["inventory_summary"]
    assert len(units) == summary["atomic_unit_count"] == 8
    assert summary["source_sufficiency_confirmed_count"] == 8
    assert all(item["source_sufficiency_review"] == "CONFIRMED" for item in units)
    assert all(item["source_page"] in {7, 8, 9} for item in units)
    assert summary["semantic_mapping_performed"] is False
    assert summary["ontology_extension_performed"] is False
    assert summary["product_specific_reasoning_added"] is False


def test_cataract_inventory_preserves_percentage_ceiling_and_both_scopes() -> None:
    units = {item["atomic_unit_id"]: item for item in _load(INVENTORY)["atomic_units"]}
    effects = set(units["star_arogya_cataract_limit"]["material_effects"])
    assert {
        "BENEFIT_LIMIT",
        "PERCENTAGE_BASIS_SUM_INSURED",
        "CURRENCY_CEILING",
        "LOWER_OF_COMPOSITION",
        "PER_EYE_SCOPE",
        "PER_POLICY_YEAR_SCOPE",
        "INSTANCE_BOUND_CURRENCY_RESULT",
    } <= effects


def test_fixed_ambulance_and_up_to_si_ayush_remain_semantically_distinct() -> None:
    units = {item["atomic_unit_id"]: item for item in _load(INVENTORY)["atomic_units"]}
    ambulance = set(units["star_arogya_road_ambulance_limit"]["material_effects"])
    ayush = set(units["star_arogya_ayush_up_to_sum_insured"]["material_effects"])
    assert "FIXED_CURRENCY" in ambulance
    assert "PER_HOSPITALIZATION_SCOPE" in ambulance
    assert "UP_TO_SUM_INSURED" in ayush
    assert "PER_POLICY_YEAR_SCOPE" in ayush
    assert "FIXED_CURRENCY" not in ayush


def test_cost_sharing_interactions_are_independent_normative_units() -> None:
    units = {item["atomic_unit_id"]: item for item in _load(INVENTORY)["atomic_units"]}
    proportionate = units["star_arogya_room_icu_proportionate_deduction"]
    copay = units["star_arogya_global_copay"]
    assert "PROPORTIONATE_DEDUCTION" in proportionate["material_effects"]
    assert "LIMIT_TRIGGERED_INTERACTION" in proportionate["material_effects"]
    assert "COPAY" in copay["material_effects"]
    assert "ALL_CLAIMS_SCOPE" in copay["material_effects"]
    assert "PAYABLE_AMOUNT_ORDERING" in copay["material_effects"]


def test_grouped_modern_treatment_limit_preserves_benefit_identity_pressure() -> None:
    units = {item["atomic_unit_id"]: item for item in _load(INVENTORY)["atomic_units"]}
    effects = set(units["star_arogya_modern_treatment_group_limit"]["material_effects"])
    assert "GROUPED_BENEFIT_SCOPE" in effects
    assert "PERCENTAGE_BASIS_SUM_INSURED" in effects
    assert "PER_POLICY_PERIOD_SCOPE" in effects


def test_room_and_icu_are_retained_as_pressure_but_not_first_slice_scope() -> None:
    units = {item["atomic_unit_id"]: item for item in _load(INVENTORY)["atomic_units"]}
    assert units["star_arogya_room_limit"]["mo028c_scope"] == "ADVERSARIAL_INTERACTION_EVIDENCE_ONLY"
    assert units["star_arogya_icu_limit"]["mo028c_scope"] == "ADVERSARIAL_INTERACTION_EVIDENCE_ONLY"
    assert units["star_arogya_room_icu_proportionate_deduction"]["mo028c_scope"] == "PRIMARY_INTERACTION_PRESSURE"


def test_g0_stops_before_limit_contract_implementation_and_routes_to_g1_identity() -> None:
    decision = _load(INVENTORY)["decision"]
    assert decision["g0_first_atomic_inventory_complete"] is True
    assert decision["ready_for_g1_benefit_identity_contract_review"] is True
    assert decision["ready_for_g2_limit_contract_implementation"] is False
