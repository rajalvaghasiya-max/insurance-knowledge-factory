from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs" / "architecture" / "hdfc_ergo_optima_secure_v8_specified_disease_waiting_period_binding_spec.json"
RULES = ROOT / "docs" / "architecture" / "hdfc_ergo_optima_secure_v8_specified_disease_material_rules_spec.json"


def test_hdfc_specified_disease_is_product_fixed_24_months() -> None:
    spec = json.loads(BASE.read_text(encoding="utf-8"))
    mechanic = spec["mechanic"]
    assert mechanic["waiting_period_type"] == "SPECIFIC_DISEASE_PROCEDURE"
    assert mechanic["duration_value"] == 24
    assert mechanic["duration_unit"] == "MONTHS"
    assert mechanic["value_source"] == "PRODUCT_FIXED"
    assert mechanic["sum_insured_enhancement_effect"] == "REAPPLIES_TO_ENHANCED_PORTION"
    assert spec["evidence_selections"] == [{
        "role": "mechanism",
        "document_id": "hdfc_ergo_optima_secure_policy_wording_v8",
        "candidate_id": "candidate_page_31",
        "candidate_text_sha256": "577c2d3bcadad71005876d367b9fe60eac8f064b83d20e872e787a7f74935327",
    }]


def test_hdfc_specified_disease_preserves_relationship_and_extra_applicability() -> None:
    spec = json.loads(RULES.read_text(encoding="utf-8"))
    rules = {item["rule_type"]: item for item in spec["material_rules"]}
    assert set(rules) == {"RELATIONSHIP_LONGER_OF", "APPLICABILITY_CONDITION"}
    assert rules["RELATIONSHIP_LONGER_OF"]["related_waiting_period_type"] == "PRE_EXISTING_DISEASE"
    assert rules["RELATIONSHIP_LONGER_OF"]["evidence_candidate_ids"] == ["candidate_page_31"]
    assert rules["APPLICABILITY_CONDITION"]["evidence_candidate_ids"] == ["candidate_page_31"]
    assert spec["governance"]["publication_authorized"] is False
    assert spec["governance"]["customer_specific_claim_determination_authorized"] is False
