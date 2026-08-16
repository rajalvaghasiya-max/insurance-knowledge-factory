from __future__ import annotations

import pytest

from insurance_intelligence.benefits.capacity_ordering import (
    CapacityNodeState,
    CapacityOrderingContractError,
    CapacityOrderNode,
    CapacityOrderRule,
    evaluate_next_capacity,
)


def activ_one_rule() -> CapacityOrderRule:
    return CapacityOrderRule(
        rule_id="current_activ_one_capacity_order_38bb",
        nodes=(
            CapacityOrderNode("BASE_SUM_INSURED"),
            CapacityOrderNode("SUPER_CREDIT", conditional=True),
            CapacityOrderNode("SUPER_RELOAD"),
            CapacityOrderNode("CANCER_BOOSTER", conditional=True),
        ),
    )


def state(capacity_id: str, *, applicability="APPLICABLE", availability="AVAILABLE", capacity_state="HAS_CAPACITY") -> CapacityNodeState:
    return CapacityNodeState(
        capacity_id=capacity_id,
        applicability=applicability,
        availability=availability,
        capacity_state=capacity_state,
    )


def test_activ_one_selects_super_credit_before_reload_when_credit_remains() -> None:
    result = evaluate_next_capacity(
        rule=activ_one_rule(),
        states=(
            state("BASE_SUM_INSURED", capacity_state="EXHAUSTED"),
            state("SUPER_CREDIT"),
            state("SUPER_RELOAD"),
            state("CANCER_BOOSTER"),
        ),
    )

    assert result.status == "SELECTED"
    assert result.selected_capacity_id == "SUPER_CREDIT"
    assert result.traversed_capacity_ids == ("BASE_SUM_INSURED",)


def test_activ_one_selects_reload_only_after_base_and_credit_are_exhausted() -> None:
    result = evaluate_next_capacity(
        rule=activ_one_rule(),
        states=(
            state("BASE_SUM_INSURED", capacity_state="EXHAUSTED"),
            state("SUPER_CREDIT", capacity_state="EXHAUSTED"),
            state("SUPER_RELOAD"),
            state("CANCER_BOOSTER"),
        ),
    )

    assert result.status == "SELECTED"
    assert result.selected_capacity_id == "SUPER_RELOAD"
    assert result.traversed_capacity_ids == ("BASE_SUM_INSURED", "SUPER_CREDIT")


def test_activ_one_optional_booster_not_opted_is_skipped_only_when_resolved() -> None:
    result = evaluate_next_capacity(
        rule=activ_one_rule(),
        states=(
            state("BASE_SUM_INSURED", capacity_state="EXHAUSTED"),
            state("SUPER_CREDIT", applicability="NOT_APPLICABLE", availability="UNAVAILABLE", capacity_state="EXHAUSTED"),
            state("SUPER_RELOAD", capacity_state="EXHAUSTED"),
            state("CANCER_BOOSTER", applicability="NOT_APPLICABLE", availability="UNAVAILABLE", capacity_state="EXHAUSTED"),
        ),
    )

    assert result.status == "NO_CAPACITY"
    assert result.selected_capacity_id is None
    assert result.traversed_capacity_ids == (
        "BASE_SUM_INSURED",
        "SUPER_CREDIT",
        "SUPER_RELOAD",
        "CANCER_BOOSTER",
    )


def test_unresolved_optional_node_blocks_traversal_instead_of_being_assumed_absent() -> None:
    result = evaluate_next_capacity(
        rule=activ_one_rule(),
        states=(
            state("BASE_SUM_INSURED", capacity_state="EXHAUSTED"),
            state("SUPER_CREDIT", applicability="UNRESOLVED", availability="UNRESOLVED", capacity_state="UNRESOLVED"),
            state("SUPER_RELOAD"),
            state("CANCER_BOOSTER", applicability="NOT_APPLICABLE", availability="UNAVAILABLE", capacity_state="EXHAUSTED"),
        ),
    )

    assert result.status == "UNRESOLVED"
    assert result.unresolved_capacity_id == "SUPER_CREDIT"
    assert result.selected_capacity_id is None


def test_materially_different_conformance_sequence_uses_same_evaluator() -> None:
    rule = CapacityOrderRule(
        rule_id="conformance_primary_restored_bonus",
        nodes=(
            CapacityOrderNode("PRIMARY_CAPACITY"),
            CapacityOrderNode("RESTORED_CAPACITY"),
            CapacityOrderNode("BONUS_CAPACITY", conditional=True),
        ),
    )

    result = evaluate_next_capacity(
        rule=rule,
        states=(
            state("PRIMARY_CAPACITY", capacity_state="EXHAUSTED"),
            state("RESTORED_CAPACITY", availability="UNAVAILABLE", capacity_state="EXHAUSTED"),
            state("BONUS_CAPACITY"),
        ),
    )

    assert result.status == "SELECTED"
    assert result.selected_capacity_id == "BONUS_CAPACITY"
    assert result.traversed_capacity_ids == ("PRIMARY_CAPACITY", "RESTORED_CAPACITY")


def test_missing_state_fails_closed_at_first_missing_node() -> None:
    result = evaluate_next_capacity(
        rule=activ_one_rule(),
        states=(state("BASE_SUM_INSURED", capacity_state="EXHAUSTED"),),
    )

    assert result.status == "UNRESOLVED"
    assert result.unresolved_capacity_id == "SUPER_CREDIT"


def test_contract_rejects_duplicate_nodes_and_unknown_state_ids() -> None:
    with pytest.raises(CapacityOrderingContractError, match="must be unique"):
        CapacityOrderRule(
            rule_id="bad",
            nodes=(CapacityOrderNode("A"), CapacityOrderNode("A")),
        )

    with pytest.raises(CapacityOrderingContractError, match="not present in rule"):
        evaluate_next_capacity(
            rule=CapacityOrderRule(rule_id="one", nodes=(CapacityOrderNode("A"),)),
            states=(state("A"), state("B")),
        )
