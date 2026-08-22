import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "docs/architecture/star_health_star_comprehensive_waiting_period_concept_pressure_inventory_2026-08-22.json"


def _data():
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


def test_star_waiting_period_inventory_keeps_concept_partial() -> None:
    data = _data()
    assert data["concept_gate"]["current_status"] == "PARTIAL"
    assert data["concept_gate"]["promotion_to_certified_authorized"] is False
    assert set(data["concept_gate"]["remaining_explicit_waiting_period_families"]) == {
        "section_ii_14_delivery_and_new_born",
        "section_ii_15_bariatric_surgery",
        "section_ii_18_preventive_health_checkup",
    }


def test_star_waiting_period_inventory_exactly_pins_outstanding_evidence() -> None:
    data = _data()
    by_benefit = {item["benefit_reference"]: item for item in data["outstanding_explicit_waiting_periods"]}
    assert by_benefit["section_ii_14_delivery_and_new_born"]["evidence"] == {
        "candidate_id": "candidate_page_14",
        "source_page": 14,
        "candidate_text_sha256": "b7af2e8c4f0669dd0b087e9c2593085d79ae40bb0e54dd22debeba70fed6d4a1",
    }
    assert by_benefit["section_ii_15_bariatric_surgery"]["evidence"] == {
        "candidate_id": "candidate_page_15",
        "source_page": 15,
        "candidate_text_sha256": "efe143eab857a4813b51c68d510d9ce7b9aafc2525c7eb6e685dcc9bd318f32c",
    }
    assert by_benefit["section_ii_18_preventive_health_checkup"]["evidence"] == {
        "candidate_id": "candidate_page_16",
        "source_page": 16,
        "candidate_text_sha256": "f23f72d57934786f73466f2ad82c1f40876bf10e3227f9018eb46e3688f2a6ed",
    }


def test_star_dental_three_year_cycle_is_not_silently_coerced_to_waiting_period() -> None:
    data = _data()
    outside = data["classified_outside_waiting_period_concept"]
    assert len(outside) == 1
    item = outside[0]
    assert item["benefit_reference"] == "section_ii_17_outpatient_dental_and_ophthalmic_treatment"
    assert item["classification"] == "TIME_GATED_BENEFIT_ELIGIBILITY_NOT_EXPLICIT_WAITING_PERIOD"
    assert data["architecture_assessment"]["dental_ophthalmic_three_year_cycle_should_not_be_forced_into_waiting_period"] is True


def test_star_inventory_rejects_named_benefit_enum_explosion() -> None:
    data = _data()
    architecture = data["architecture_assessment"]
    assert architecture["existing_scope_type_supports_benefit_scope"] is True
    assert architecture["existing_waiting_period_type_enum_supports_arbitrary_benefit_waits"] is False
    assert architecture["enum_expansion_per_named_benefit_authorized"] is False
    assert architecture["preferred_generic_extension"] == "BENEFIT_SPECIFIC waiting-period type with BENEFIT_SCOPED scope_reference"
