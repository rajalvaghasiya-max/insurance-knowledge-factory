import json
from pathlib import Path

from insurance_intelligence.coverage_registry.contracts import ConceptCoverageStatus
from insurance_intelligence.coverage_registry.health_seed import STAR_COMPREHENSIVE_COVERAGE


ROOT = Path(__file__).resolve().parents[2]
CLOSURE_PATH = ROOT / "docs/architecture/star_health_star_comprehensive_waiting_period_concept_certification_closure_2026-08-22.json"


def _waiting_period_record():
    return next(item for item in STAR_COMPREHENSIVE_COVERAGE.concepts if item.concept_id == "waiting_period")


def test_star_waiting_period_concept_is_certified_only_after_full_audited_scope_closure() -> None:
    record = _waiting_period_record()
    assert record.status is ConceptCoverageStatus.CERTIFIED
    assert record.comparison_ready is False
    assert record.decision_support_ready is False


def test_star_waiting_period_closure_records_all_governed_explicit_waits() -> None:
    closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
    mechanics = closure["certified_mechanics"]
    assert [(item["mechanic"], item.get("scope_reference")) for item in mechanics] == [
        ("INITIAL", None),
        ("PRE_EXISTING_DISEASE_STANDARD", None),
        ("PRE_EXISTING_DISEASE_OPTIONAL_BUYBACK", None),
        ("SPECIFIC_DISEASE_PROCEDURE", None),
        ("BENEFIT_SPECIFIC", "section_ii_14_delivery_and_new_born"),
        ("BENEFIT_SPECIFIC", "section_ii_15_bariatric_surgery"),
        ("BENEFIT_SPECIFIC", "section_ii_18_preventive_health_checkup"),
    ]


def test_star_waiting_period_closure_keeps_dental_ophthalmic_time_gate_outside_concept() -> None:
    closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
    scope = closure["scope_classification"]
    assert scope["all_current_base_policy_clauses_explicitly_expressed_as_waiting_periods_are_governed"] is True
    assert scope["section_ii_17_dental_ophthalmic_three_year_cycle_in_waiting_period"] is False
    assert scope["section_ii_17_classification"] == "TIME_GATED_BENEFIT_ELIGIBILITY_NOT_EXPLICIT_WAITING_PERIOD"


def test_star_waiting_period_closure_does_not_authorize_downstream_use() -> None:
    closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
    governance = closure["governance_boundary"]
    assert governance["publication_authorized"] is False
    assert governance["comparison_ready"] is False
    assert governance["decision_support_ready"] is False
    assert governance["customer_specific_eligibility_authorized"] is False
    assert governance["claim_payment_prediction_authorized"] is False
    assert governance["optional_ped_buyback_selection_inferred_without_policy_evidence"] is False
