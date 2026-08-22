from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ARCH = REPOSITORY_ROOT / "docs" / "architecture"
SPEC = ARCH / "bajaj_my_health_care_v2_copayment_binding_spec.json"
INVENTORY = ARCH / "bajaj_my_health_care_v2_copayment_evidence_inventory_2026-08-22.json"

EXPECTED = {
    "ga_bajaj_my_health_care_lab_radiology_unapproved_reimbursement_copay_v1": (
        "candidate_page_15",
        "e847a43f632bf01e2ce1d5e6c32d696a402153a5001d2c7970acb8bd79d3c7e6",
    ),
    "ga_bajaj_my_health_care_international_emergency_mandatory_copay_v1": (
        "candidate_page_20",
        "5261b13c20af365078c7ec1a4b43e742fd1890257a57fa5858d6314eff87aef2",
    ),
    "ga_bajaj_my_health_care_voluntary_inpatient_copay_v1": (
        "candidate_page_33",
        "47fabdbf4992a88c89bc8147bffd4c4241a52304fc9d683c52f0854c1097fcce",
    ),
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_binding_spec_uses_three_distinct_primary_legal_candidates() -> None:
    spec = _load(SPEC)

    assert spec["binding_type"] == "generic_legal_condition_binding_v1"
    assert spec["reviewed_by_human"] is True
    assert spec["generic_source_bundle_path"].endswith(
        "/v2/generic_source_registration/bajaj_my_health_care_v2_generic_source_bundle.json"
    )
    assert len(spec["assertions"]) == 3

    actual = {}
    for assertion in spec["assertions"]:
        assert assertion["assertion_type"] == "conditional_copayment_rule"
        assert len(assertion["evidence_selections"]) == 1
        evidence = assertion["evidence_selections"][0]
        assert evidence["document_id"] == "bajaj_my_health_care_policy_wording_v2"
        actual[assertion["assertion_id"]] = (
            evidence["candidate_id"],
            evidence["candidate_text_sha256"],
        )

    assert actual == EXPECTED


def test_binding_spec_preserves_mechanism_specific_semantics() -> None:
    spec = _load(SPEC)
    by_id = {item["assertion_id"]: item for item in spec["assertions"]}

    lab = by_id["ga_bajaj_my_health_care_lab_radiology_unapproved_reimbursement_copay_v1"]
    assert "20%" in lab["reviewed_statement"]
    assert "not pre-approved" in lab["reviewed_statement"]
    assert "investigations cover" in lab["reviewed_statement"]

    international = by_id["ga_bajaj_my_health_care_international_emergency_mandatory_copay_v1"]
    assert "mandatory 10%" in international["reviewed_statement"]
    assert "additional to any other co-payment or deductible" in international["reviewed_statement"]
    assert "international emergency cover" in international["reviewed_statement"]

    voluntary = by_id["ga_bajaj_my_health_care_voluntary_inpatient_copay_v1"]
    for rate in ("5%", "10%", "15%", "20%"):
        assert rate in voluntary["reviewed_statement"]
    assert "In-patient Hospitalization Treatment" in voluntary["reviewed_statement"]
    assert "selected voluntary co-payment option" in voluntary["reviewed_statement"]


def test_binding_spec_does_not_flatten_to_one_product_level_copayment() -> None:
    spec = _load(SPEC)
    semantic_keys = {item["semantic_key"] for item in spec["assertions"]}

    assert len(semantic_keys) == 3
    assert "copayment.product_level" not in semantic_keys
    assert all("single product-level co-payment" not in item["semantic_key"] for item in spec["assertions"])


def test_binding_spec_is_consistent_with_governed_inventory() -> None:
    spec = _load(SPEC)
    inventory = _load(INVENTORY)

    assert inventory["governance_decision"]["single_product_level_copayment_fact"] == "PROHIBITED"
    assert inventory["governance_decision"]["architecture_change"] == "NONE"
    assert len(inventory["mechanisms"]) == len(spec["assertions"]) == 3
