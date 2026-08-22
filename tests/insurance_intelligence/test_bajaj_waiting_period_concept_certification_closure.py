import json
from pathlib import Path


CLOSURE_PATH = Path(
    "docs/architecture/"
    "bajaj_my_health_care_v2_waiting_period_concept_certification_closure_2026-08-22.json"
)


def _closure() -> dict:
    return json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))


def test_waiting_period_concept_closure_certifies_all_five_families() -> None:
    closure = _closure()
    assert closure["concept_id"] == "waiting_period"
    assert closure["concept_status"] == "CERTIFIED"
    assert closure["comparison_ready"] is False
    assert closure["decision_support_ready"] is False
    assert closure["publication_authorized"] is False

    families = {
        item["waiting_period_type"]: item
        for item in closure["certified_families"]
    }
    assert set(families) == {
        "INITIAL",
        "PRE_EXISTING_DISEASE",
        "SPECIFIC_DISEASE_PROCEDURE",
        "MATERNITY",
        "BABY_CARE",
    }
    assert all(item["certification_outcome"] == "PASS" for item in families.values())
    assert all(item["completeness"] == "COMPLETE" for item in families.values())
    assert all(item["explanation_permitted"] is True for item in families.values())


def test_option_domain_certification_does_not_imply_selected_customer_duration() -> None:
    closure = _closure()
    families = {
        item["waiting_period_type"]: item
        for item in closure["certified_families"]
    }
    for family_id in ("PRE_EXISTING_DISEASE", "SPECIFIC_DISEASE_PROCEDURE"):
        family = families[family_id]
        assert family["resolution_level"] == "CERTIFIED_UNRESOLVED_SCHEDULE_OPTION_DOMAIN"
        assert family["authoritative_options"] == ["1 YEAR", "2 YEARS", "3 YEARS"]
        assert family["policy_instance_selected_duration"] == "UNRESOLVED_WITHOUT_POLICY_SCHEDULE"

    boundary = closure["governance_boundary"]
    assert boundary["concept_certified"] is True
    assert boundary["customer_specific_schedule_resolution_is_not_implied"] is True
    assert boundary["ped_and_specific_disease_selected_duration_requires_policy_schedule"] is True
    assert boundary["comparison_ready"] is False
    assert boundary["decision_support_ready"] is False
    assert boundary["publication_authorized"] is False
    assert boundary["claim_payment_prediction_authorized"] is False


def test_maternity_and_baby_care_closure_preserves_36_to_24_month_reduction() -> None:
    closure = _closure()
    families = {
        item["waiting_period_type"]: item
        for item in closure["certified_families"]
    }
    for family_id in ("MATERNITY", "BABY_CARE"):
        family = families[family_id]
        assert family["resolution_level"] == "RESOLVED_SCALAR_WITH_CERTIFIED_MODIFICATION"
        joined = " | ".join(family["material_semantics"])
        assert "36 MONTHS" in joined
        assert "REDUCTION to 24 MONTHS" in joined
