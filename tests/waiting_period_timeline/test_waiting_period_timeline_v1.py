from pathlib import Path
import json

import pytest

from knowledge_domains.health.waiting_period_timeline import (
    WaitingPeriodTimelineSimulationCell,
)


def test_30_day_timeline_becomes_active_on_activation_date(tmp_path: Path):
    outputs = WaitingPeriodTimelineSimulationCell(output_dir=tmp_path).run(
        policy_start_date="2026-01-01",
        claim_date="2026-01-31",
        waiting_period_type="initial_waiting_period",
        waiting_period_value=30,
        waiting_period_unit="days",
        activation_convention="ON_OR_AFTER_CALCULATED_DATE",
    )

    asset = json.loads(Path(outputs["asset"]).read_text(encoding="utf-8"))

    assert (
    asset["timeline_assessment"]["calculated_boundary_date"]
    == "2026-01-31"
    )
    assert (
        asset["timeline_assessment"]["first_active_date"]
        == "2026-01-31"
    )
    assert asset["timeline_assessment"]["timeline_status"] == "ACTIVE"
    assert asset["certification_status"] == "PASS"


def test_three_year_ped_timeline_is_not_active_before_completion(tmp_path: Path):
    outputs = WaitingPeriodTimelineSimulationCell(output_dir=tmp_path).run(
        policy_start_date="2026-01-01",
        claim_date="2027-06-01",
        waiting_period_type="pre_existing_disease_waiting_period",
        waiting_period_value=3,
        waiting_period_unit="years",
        activation_convention="ON_OR_AFTER_CALCULATED_DATE",
    )

    asset = json.loads(Path(outputs["asset"]).read_text(encoding="utf-8"))

    assert (
    asset["timeline_assessment"]["calculated_boundary_date"]
    == "2029-01-01"
    )
    assert (
        asset["timeline_assessment"]["first_active_date"]
        == "2029-01-01"
    )
    assert asset["timeline_assessment"]["timeline_status"] == "NOT_ACTIVE"
    assert "does not confirm final claim approval" in (
        asset["explanation"]["what_this_does_not_mean"].lower()
    )


def test_two_year_specific_disease_timeline_becomes_active(tmp_path: Path):
    outputs = WaitingPeriodTimelineSimulationCell(output_dir=tmp_path).run(
        policy_start_date="2026-01-01",
        claim_date="2028-01-01",
        waiting_period_type="specific_disease_waiting_period",
        waiting_period_value=24,
        waiting_period_unit="months",
        activation_convention="ON_OR_AFTER_CALCULATED_DATE",
    )

    asset = json.loads(Path(outputs["asset"]).read_text(encoding="utf-8"))

    assert (
    asset["timeline_assessment"]["calculated_boundary_date"]
    == "2028-01-01"
    )
    assert (
        asset["timeline_assessment"]["first_active_date"]
        == "2028-01-01"
    )
    assert asset["timeline_assessment"]["timeline_status"] == "ACTIVE"


def test_after_completion_convention_is_not_active_on_calculated_date(tmp_path):
    cell = WaitingPeriodTimelineSimulationCell(output_dir=tmp_path)

    outputs = cell.run(
        policy_start_date="2026-01-01",
        claim_date="2026-01-31",
        waiting_period_type="initial_waiting_period",
        waiting_period_value=30,
        waiting_period_unit="days",
        activation_convention="AFTER_COMPLETION_OF_PERIOD",
    )

    asset = json.loads(
        Path(outputs["asset"]).read_text(encoding="utf-8")
    )

    assessment = asset["timeline_assessment"]

    assert assessment["calculated_boundary_date"] == "2026-01-31"
    assert assessment["first_active_date"] == "2026-02-01"
    assert assessment["timeline_status"] == "NOT_ACTIVE"
    assert assessment["waiting_period_complete"] is False

def test_invalid_timeline_inputs_are_rejected(tmp_path: Path):
    cell = WaitingPeriodTimelineSimulationCell(output_dir=tmp_path)

    with pytest.raises(ValueError, match="claim_date cannot be earlier"):
        cell.run(
            policy_start_date="2026-01-01",
            claim_date="2025-12-31",
            waiting_period_type="initial_waiting_period",
            waiting_period_value=30,
            waiting_period_unit="days",
            activation_convention="ON_OR_AFTER_CALCULATED_DATE",
        )

    with pytest.raises(ValueError, match="Unsupported waiting_period_unit"):
        cell.run(
            policy_start_date="2026-01-01",
            claim_date="2026-03-01",
            waiting_period_type="initial_waiting_period",
            waiting_period_value=30,
            waiting_period_unit="weeks",
            activation_convention="ON_OR_AFTER_CALCULATED_DATE",
        )