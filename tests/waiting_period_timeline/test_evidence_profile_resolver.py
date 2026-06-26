from pathlib import Path

import pytest

from knowledge_domains.health.waiting_period_timeline.evidence_profile_resolver import (
    WaitingPeriodEvidenceProfileResolver,
)


PROFILE_PATH = Path(
    "knowledge/factory/golden_concepts/waiting_period/"
    "waiting_period_timeline_evidence_profile.json"
)

EXAMPLE_ID = "activ_one_c10_1_reduced_specific_disease_1_year"


def test_resolver_returns_requested_fully_specified_example():
    scenario = WaitingPeriodEvidenceProfileResolver(
        PROFILE_PATH
    ).resolve_example(EXAMPLE_ID)

    assert scenario["example_id"] == EXAMPLE_ID
    assert scenario["concept_id"] == "waiting_period"
    assert (
        scenario["waiting_period_type"]
        == "reduced_specific_disease_waiting_period"
    )
    assert scenario["waiting_period_value"] == 1
    assert scenario["waiting_period_unit"] == "years"
    assert (
        scenario["activation_convention"]
        == "AFTER_COMPLETION_OF_PERIOD"
    )


def test_resolver_rejects_unknown_example_id():
    with pytest.raises(ValueError, match="No evidence-backed example found"):
        WaitingPeriodEvidenceProfileResolver(
            PROFILE_PATH
        ).resolve_example("unknown_example")
