import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs" / "architecture"

EXPECTED = {
    "tata_aig_medicare_premier_initial_waiting_period_binding_spec.json": ("INITIAL", 30, "DAYS", "candidate_page_34", "1a7ab46d49e074c62390343954b4609059f73a1dc44774cb78fb062b1b95ac8d"),
    "tata_aig_medicare_premier_specified_disease_waiting_period_binding_spec.json": ("SPECIFIC_DISEASE_PROCEDURE", 24, "MONTHS", "candidate_page_34", "1a7ab46d49e074c62390343954b4609059f73a1dc44774cb78fb062b1b95ac8d"),
    "tata_aig_medicare_premier_ped_waiting_period_binding_spec.json": ("PRE_EXISTING_DISEASE", 24, "MONTHS", "candidate_page_36", "45abbedf48bfcab0d7c7df505da3447b185263b4cfd950d75da4bccfa69e742e"),
    "tata_aig_medicare_premier_vaccination_waiting_period_binding_spec.json": ("BENEFIT_SPECIFIC", 24, "MONTHS", "candidate_page_18", "469cdde4cff5a39468e845985af8f9f88023b2afa33fac9a90c3773d2c60186f"),
    "tata_aig_medicare_premier_maternity_waiting_period_binding_spec.json": ("BENEFIT_SPECIFIC", 36, "MONTHS", "candidate_page_20", "a78753a0bef77f4ea68a3658c35475bb47b7d1ca6365170372136383a47bb0d2"),
    "tata_aig_medicare_premier_opd_waiting_period_binding_spec.json": ("BENEFIT_SPECIFIC", 24, "MONTHS", "candidate_page_21", "902a3c4eab1e14922b0f94ce7c0b8dfd848a0cf54024e0e13d9562388ccadbd6"),
    "tata_aig_medicare_premier_opd_dental_waiting_period_binding_spec.json": ("BENEFIT_SPECIFIC", 24, "MONTHS", "candidate_page_22", "4068afe22f02078f0376a02ac798679731788d1c24b2b74c1eb4916e1d1fbcf1"),
}


def _load(name: str):
    return json.loads((DOCS / name).read_text(encoding="utf-8"))


def test_all_tata_waiting_period_specs_use_existing_scalar_binding_contract() -> None:
    for name, (kind, value, unit, candidate, digest) in EXPECTED.items():
        spec = _load(name)
        assert spec["binding_type"] == "waiting_period_binding_v1"
        assert spec["manufacturing_status"] == "resolved_scalar_ready_for_binding"
        assert spec["reviewed_by_human"] is True
        mechanic = spec["mechanic"]
        assert mechanic["waiting_period_type"] == kind
        assert mechanic["duration_value"] == value
        assert mechanic["duration_unit"] == unit
        evidence = spec["evidence_selections"]
        assert len(evidence) == 1
        assert evidence[0]["candidate_id"] == candidate
        assert evidence[0]["candidate_text_sha256"] == digest
        assert evidence[0]["document_id"] == "tata_aig_medicare_premier_policy_wording_v5"
        assert spec["governance"]["publication_authorized"] is False
        assert spec["governance"]["policy_specific_eligibility_authorized"] is False
        assert spec["governance"]["cold_start_runtime_python_changes"] == 0


def test_benefit_specific_waits_remain_benefit_scoped() -> None:
    names = [
        "tata_aig_medicare_premier_vaccination_waiting_period_binding_spec.json",
        "tata_aig_medicare_premier_maternity_waiting_period_binding_spec.json",
        "tata_aig_medicare_premier_opd_waiting_period_binding_spec.json",
        "tata_aig_medicare_premier_opd_dental_waiting_period_binding_spec.json",
    ]
    for name in names:
        mechanic = _load(name)["mechanic"]
        assert mechanic["scope_type"] == "BENEFIT_SCOPED"
        assert mechanic["scope_reference"]


def test_tata_material_rules_reuse_existing_generic_rule_types() -> None:
    specified = _load("tata_aig_medicare_premier_specified_disease_material_rules_spec.json")
    assert [rule["rule_type"] for rule in specified["material_rules"]] == [
        "RELATIONSHIP_LONGER_OF",
        "APPLICABILITY_CONDITION",
    ]
    assert all(rule["evidence_candidate_ids"] == ["candidate_page_34"] for rule in specified["material_rules"])

    ped = _load("tata_aig_medicare_premier_ped_material_rules_spec.json")
    assert [rule["rule_type"] for rule in ped["material_rules"]] == ["POST_WAIT_CONDITION"]
    assert ped["material_rules"][0]["evidence_candidate_ids"] == ["candidate_page_36"]


def test_tata_waiting_period_specs_do_not_manufacture_customer_specific_truth() -> None:
    for name in EXPECTED:
        spec = _load(name)
        assert spec["mechanic"]["value_source"] == "PRODUCT_FIXED"
        assert spec["mechanic"]["schedule_dependency"] is None
        assert spec["governance"]["policy_specific_eligibility_authorized"] is False
