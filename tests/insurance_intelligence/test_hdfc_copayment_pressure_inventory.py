import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "docs/architecture/hdfc_ergo_optima_secure_v8_copayment_pressure_inventory_2026-08-23.json"


def _inventory():
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def test_hdfc_copayment_definition_is_not_promoted_to_product_obligation() -> None:
    inventory = _inventory()
    definition = inventory["reviewed_occurrences"][0]
    assert definition["occurrence_type"] == "DEFINITION_ONLY"
    assert definition["binding_authorized"] is False
    assert inventory["pressure_assessment"]["definition_may_not_be_used_as_product_obligation"] is True


def test_hdfc_current_wording_exposes_explicit_no_copayment_rule() -> None:
    inventory = _inventory()
    rule = inventory["reviewed_occurrences"][1]
    assert rule["source_page"] == 44
    assert rule["occurrence_type"] == "EXPLICIT_NO_COPAYMENT_RULE"
    assert rule["section"] == "1.24 Premium Tier"
    assert "No co-payment shall apply" in rule["reviewed_meaning"]
    assert inventory["pressure_assessment"]["positive_percentage_copayment_found_in_reviewed_current_wording"] is False


def test_hdfc_no_copayment_pressure_does_not_fake_zero_percent_positive_obligation() -> None:
    inventory = _inventory()
    pressure = inventory["pressure_assessment"]
    assert pressure["existing_positive_conditional_copayment_path_is_sufficient"] is False
    assert pressure["architecture_pressure"] == "REPRESENT_EXPLICIT_NO_COPAYMENT_WITHOUT_FABRICATING_POSITIVE_PERCENTAGE"
    assert inventory["candidate_binding_gate"]["exact_registered_candidate_hashes_required_before_binding"] is True


def test_hdfc_copayment_inventory_does_not_authorize_registry_promotion() -> None:
    governance = _inventory()["governance"]
    assert governance["copayment_concept_certified"] is False
    assert governance["publication_authorized"] is False
    assert governance["coverage_registry_promotion_authorized"] is False
    assert governance["comparison_ready_authorized"] is False
    assert governance["decision_support_ready_authorized"] is False
