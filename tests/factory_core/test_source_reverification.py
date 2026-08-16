from __future__ import annotations

import pytest

from factory_core.governance.source_reverification import (
    ANCHOR_MATCH,
    CONTINUE,
    REVERIFICATION_REQUIRED,
    WITHHELD,
    SourceReverificationContractError,
    assess_source_anchor,
    record_source_reverification,
)


HISTORICAL = "9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade"
CURRENT = "05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158"


def test_matching_anchor_can_continue_without_reverification():
    result = assess_source_anchor(
        reviewed_source_sha256=CURRENT,
        current_source_sha256=CURRENT,
    )

    assert result.anchor_status == ANCHOR_MATCH
    assert result.flow_state == CONTINUE
    assert result.withhold_reason is None


def test_bajaj_historical_anchor_is_withheld_for_current_reverification():
    result = assess_source_anchor(
        reviewed_source_sha256=HISTORICAL,
        current_source_sha256=CURRENT,
    )

    assert result.anchor_status == REVERIFICATION_REQUIRED
    assert result.flow_state == WITHHELD
    assert result.withhold_reason == "source_reverification_required"


def test_confirmed_reverification_allows_prior_semantic_fact_to_continue():
    anchor = assess_source_anchor(
        reviewed_source_sha256=HISTORICAL,
        current_source_sha256=CURRENT,
    )

    result = record_source_reverification(
        anchor=anchor,
        outcome="CONFIRMED",
        evidence_reference="governance/bajaj_initial_wait_current_05dc.json",
    )

    assert result.outcome == "CONFIRMED"
    assert result.flow_state == CONTINUE
    assert result.withhold_reason is None
    assert result.prior_semantic_fact_reusable is True


@pytest.mark.parametrize(
    ("outcome", "reason"),
    [
        ("DIFFERS", "current_source_differs_semantic_review_required"),
        ("NOT_PRESENT", "current_source_proposition_not_present"),
        ("AMBIGUOUS", "current_source_reverification_ambiguous"),
    ],
)
def test_nonconfirming_reverification_remains_withheld(outcome, reason):
    anchor = assess_source_anchor(
        reviewed_source_sha256=HISTORICAL,
        current_source_sha256=CURRENT,
    )

    result = record_source_reverification(
        anchor=anchor,
        outcome=outcome,
        evidence_reference="governance/current_source_review.json",
    )

    assert result.flow_state == WITHHELD
    assert result.withhold_reason == reason
    assert result.prior_semantic_fact_reusable is False


def test_reverification_cannot_be_recorded_when_anchor_is_already_current():
    anchor = assess_source_anchor(
        reviewed_source_sha256=CURRENT,
        current_source_sha256=CURRENT,
    )

    with pytest.raises(SourceReverificationContractError, match="REVERIFICATION_REQUIRED"):
        record_source_reverification(
            anchor=anchor,
            outcome="CONFIRMED",
            evidence_reference="governance/current_source_review.json",
        )


def test_invalid_sha_fails_closed():
    with pytest.raises(SourceReverificationContractError, match="64-character"):
        assess_source_anchor(
            reviewed_source_sha256="abc",
            current_source_sha256=CURRENT,
        )


def test_unknown_reverification_outcome_fails_closed():
    anchor = assess_source_anchor(
        reviewed_source_sha256=HISTORICAL,
        current_source_sha256=CURRENT,
    )

    with pytest.raises(SourceReverificationContractError, match="outcome must be one of"):
        record_source_reverification(
            anchor=anchor,
            outcome="PROBABLY_SAME",
            evidence_reference="governance/current_source_review.json",
        )
