from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.check_health_repeatability_scorecard import (
    RepeatabilityScorecardError,
    evaluate_scorecard,
    validate_scorecard,
)


def _base():
    return {
        "schema_version": "1.0",
        "gate_issue": 355,
        "experiment_id": "health-repeatability-v1",
        "baseline": {
            "ordinal": 1,
            "concept_id": "pre_existing_disease",
            "measurement_status": "LEGACY_BASELINE_NOT_SCORED",
        },
        "experiments": [],
    }


def _concept(ordinal, *, repairs=0, product_runtime=0, modified_runtime=False):
    return {
        "ordinal": ordinal,
        "concept_id": f"concept_{ordinal}",
        "status": "COMPLETE",
        "front_half_autonomy_level": "A2",
        "data_only_count": 1,
        "generic_extension_count": 0,
        "architecture_repair_count": repairs,
        "bug_fix_count": 0,
        "product_specific_runtime_count": product_runtime,
        "repair_cycles_to_first_acceptable_answer": 0,
        "modified_existing_shared_runtime": modified_runtime,
        "questions": {
            "tested": 3,
            "acceptable": 2,
            "correct_fail_closed": 1,
            "unacceptable": 0,
        },
        "authority_fidelity": "PASS",
    }


def test_empty_preregistered_scorecard_is_valid_and_pending():
    evaluation = evaluate_scorecard(_base())
    assert evaluation.status == "PENDING"
    assert evaluation.completed_concepts == 0
    assert evaluation.architecture_repair_average is None


def test_ped_baseline_cannot_be_retroactively_scored():
    data = _base()
    data["baseline"]["measurement_status"] = "COMPLETE"
    with pytest.raises(RepeatabilityScorecardError, match="LEGACY_BASELINE_NOT_SCORED"):
        validate_scorecard(data)


def test_question_outcomes_must_reconcile():
    data = _base()
    item = _concept(2)
    item["questions"]["tested"] = 4
    data["experiments"] = [item]
    with pytest.raises(RepeatabilityScorecardError, match="must equal"):
        validate_scorecard(data)


def test_product_specific_runtime_is_immediate_platform_review():
    data = _base()
    data["experiments"] = [_concept(2, repairs=1, product_runtime=1)]
    evaluation = evaluate_scorecard(data)
    assert evaluation.status == "PLATFORM_REVIEW"
    assert "product-specific runtime branch introduced" in evaluation.reasons


def test_average_architecture_repair_threshold_is_frozen_at_half_per_concept():
    data = _base()
    data["experiments"] = [
        _concept(2, repairs=1, modified_runtime=True),
        _concept(3),
        _concept(4, repairs=1, modified_runtime=True),
        _concept(5, repairs=1, modified_runtime=True),
    ]
    evaluation = evaluate_scorecard(data)
    assert evaluation.architecture_repair_average == 0.75
    assert evaluation.status == "PLATFORM_REVIEW"
    assert "average architecture repair count exceeds 0.5 per concept" in evaluation.reasons


def test_concepts_four_and_five_both_requiring_repair_trips_platform_review():
    data = _base()
    data["experiments"] = [
        _concept(2),
        _concept(3),
        _concept(4, repairs=1, modified_runtime=True),
        _concept(5, repairs=1, modified_runtime=True),
    ]
    evaluation = evaluate_scorecard(data)
    assert evaluation.status == "PLATFORM_REVIEW"
    assert "concepts #4 and #5 both required architecture repair" in evaluation.reasons


def test_full_gate_pass_requires_two_consecutive_no_shared_runtime_modifications():
    data = _base()
    data["experiments"] = [
        _concept(2, repairs=1, modified_runtime=True),
        _concept(3),
        _concept(4),
        _concept(5),
    ]
    evaluation = evaluate_scorecard(data)
    assert evaluation.architecture_repair_average == 0.25
    assert evaluation.consecutive_no_shared_runtime_modification is True
    assert evaluation.status == "PASS"


def test_full_gate_fails_without_two_consecutive_clean_runtime_onboards():
    data = _base()
    data["experiments"] = [
        _concept(2, repairs=1, modified_runtime=True),
        _concept(3),
        _concept(4, repairs=1, modified_runtime=True),
        _concept(5),
    ]
    evaluation = evaluate_scorecard(data)
    assert evaluation.status == "PLATFORM_REVIEW"
    assert evaluation.consecutive_no_shared_runtime_modification is False


def test_in_progress_experiment_may_keep_authority_fidelity_pending():
    data = _base()
    item = _concept(2)
    item["status"] = "IN_PROGRESS"
    item["authority_fidelity"] = "PENDING"
    data["experiments"] = [item]
    validate_scorecard(data)
    assert evaluate_scorecard(data).status == "PENDING"


def test_complete_experiment_must_resolve_authority_fidelity():
    data = _base()
    item = _concept(2)
    item["authority_fidelity"] = "PENDING"
    data["experiments"] = [item]
    with pytest.raises(RepeatabilityScorecardError, match="authority_fidelity"):
        validate_scorecard(data)


def test_failed_customer_quality_does_not_count_as_clean_onboarding():
    data = _base()
    concept3 = _concept(3)
    concept3["questions"] = {
        "tested": 4,
        "acceptable": 0,
        "correct_fail_closed": 0,
        "unacceptable": 4,
    }
    data["experiments"] = [
        _concept(2, repairs=1, modified_runtime=True),
        concept3,
        _concept(4, repairs=1, modified_runtime=True),
        _concept(5),
    ]

    evaluation = evaluate_scorecard(data)

    assert evaluation.architecture_repair_average == 0.5
    assert evaluation.consecutive_no_shared_runtime_modification is False
    assert evaluation.status == "PLATFORM_REVIEW"
    assert (
        "no two consecutive concepts onboarded without modifying existing shared runtime"
        in evaluation.reasons
    )
