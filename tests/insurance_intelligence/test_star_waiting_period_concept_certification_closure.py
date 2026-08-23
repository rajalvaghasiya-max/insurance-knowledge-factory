import json
from pathlib import Path

from insurance_intelligence.coverage_registry.contracts import ConceptCoverageStatus
from insurance_intelligence.coverage_registry.health_seed import STAR_COMPREHENSIVE_COVERAGE


ROOT = Path(__file__).resolve().parents[2]
CLOSURE_PATH = ROOT / "docs/architecture/star_health_star_comprehensive_waiting_period_concept_certification_closure_2026-08-23.json"


def _waiting_period_record():
    return next(item for item in STAR_COMPREHENSIVE_COVERAGE.concepts if item.concept_id == "waiting_period")


def test_star_waiting_period_concept_is_certified_only_after_full_audited_scope_closure() -> None:
    record = _waiting_period_record()
    assert record.status is ConceptCoverageStatus.CERTIFIED
    assert record.comparison_ready is False
    assert record.decision_support_ready is False


def test_star_waiting_period_closure_records_all_governed_explicit_waits() -> None:
    closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
    governed = closure["governed_waiting_periods"]
    assert {item["concept_slice"] for item in governed} == {
        "initial",
        "pre_existing_disease",
        "ped_optional_buyback",
        "specified_disease_procedure",
        "delivery_and_new_born",
        "bariatric_surgery",
        "preventive_health_checkup",
    }


def test_star_waiting_period_closure_keeps_dental_ophthalmic_time_gate_outside_concept() -> None:
    closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
    excluded = closure["explicit_scope_exclusions"]
    assert excluded == [
        {
            "section": "II.17",
            "topic": "out_patient_dental_and_ophthalmic_treatment",
            "classification": "time_gated_benefit_eligibility_not_waiting_period",
            "reason": "The wording requires a block of continuous coverage for eligibility but does not express this as a waiting period.",
        }
    ]


def test_star_waiting_period_closure_does_not_authorize_downstream_use() -> None:
    closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
    governance = closure["governance"]
    assert governance["publication_authorized"] is False
    assert governance["comparison_ready_authorized"] is False
    assert governance["decision_support_ready_authorized"] is False
    assert governance["customer_specific_eligibility_authorized"] is False
    assert governance["claim_payment_prediction_authorized"] is False
