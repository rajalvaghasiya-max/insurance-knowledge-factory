import json
from pathlib import Path

from knowledge_domains.health.waiting_period_timeline.evidence_backed_timeline_runner import (
    EvidenceBackedWaitingPeriodTimelineRunner,
)


def test_runner_uses_approved_evidence_profile_example(tmp_path: Path):
    profile_path = Path(
        "knowledge/factory/golden_concepts/waiting_period/"
        "waiting_period_timeline_evidence_profile.json"
    )

    outputs = EvidenceBackedWaitingPeriodTimelineRunner(
        evidence_profile_path=profile_path,
        output_dir=tmp_path,
    ).run(
        policy_start_date="2026-01-01",
        claim_date="2027-01-01",
    )

    asset = json.loads(
        Path(outputs["asset"]).read_text(encoding="utf-8")
    )

    assert (
        asset["scenario"]["waiting_period_type"]
        == "reduced_specific_disease_waiting_period"
    )
    assert asset["scenario"]["waiting_period_value"] == 1
    assert asset["scenario"]["waiting_period_unit"] == "years"
    assert (
        asset["scenario"]["activation_convention"]
        == "AFTER_COMPLETION_OF_PERIOD"
    )

    assert (
        asset["timeline_assessment"]["calculated_boundary_date"]
        == "2027-01-01"
    )
    assert (
        asset["timeline_assessment"]["first_active_date"]
        == "2027-01-02"
    )
    assert asset["timeline_assessment"]["timeline_status"] == "NOT_ACTIVE"

    assert (
        asset["source_assets"]["scope"]
        == "Optional Cover C.10.1 only"
    )