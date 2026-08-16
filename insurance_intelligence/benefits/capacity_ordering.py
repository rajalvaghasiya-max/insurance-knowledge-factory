"""Insurer-independent evaluation of bounded ordered insurance capacity chains.

This module answers one narrow question: given a governed ordered capacity chain
and claim-time state for each node, which capacity is next eligible to be
consumed? It does not calculate claim payment, capacity amounts, copay,
deductible, waiting-period eligibility, or arbitrary benefit interactions.
"""
from __future__ import annotations

from dataclasses import dataclass


APPLICABILITY_STATES = frozenset({"APPLICABLE", "NOT_APPLICABLE", "UNRESOLVED"})
AVAILABILITY_STATES = frozenset({"AVAILABLE", "UNAVAILABLE", "UNRESOLVED"})
CAPACITY_STATES = frozenset({"HAS_CAPACITY", "EXHAUSTED", "UNRESOLVED"})
RESULT_STATUSES = frozenset({"SELECTED", "NO_CAPACITY", "UNRESOLVED"})


class CapacityOrderingContractError(ValueError):
    """Raised when ordered-capacity configuration or state is invalid."""


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CapacityOrderingContractError(f"{label} must be non-empty text")
    return value.strip()


def _member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise CapacityOrderingContractError(
            f"{label} must be one of {sorted(allowed)}; got {value!r}"
        )
    return str(value)


@dataclass(frozen=True)
class CapacityOrderNode:
    """One governed node in an ordered insurance-capacity chain."""

    capacity_id: str
    conditional: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "capacity_id", _required_text(self.capacity_id, "capacity_id"))
        if not isinstance(self.conditional, bool):
            raise CapacityOrderingContractError("conditional must be boolean")


@dataclass(frozen=True)
class CapacityOrderRule:
    """Closed declarative ordering rule independent of insurer/product identity."""

    rule_id: str
    nodes: tuple[CapacityOrderNode, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", _required_text(self.rule_id, "rule_id"))
        if not isinstance(self.nodes, tuple) or not self.nodes:
            raise CapacityOrderingContractError("nodes must be a non-empty tuple")
        if not all(isinstance(node, CapacityOrderNode) for node in self.nodes):
            raise CapacityOrderingContractError("nodes must contain CapacityOrderNode values")
        ids = tuple(node.capacity_id for node in self.nodes)
        if len(ids) != len(set(ids)):
            raise CapacityOrderingContractError("capacity_id values must be unique")


@dataclass(frozen=True)
class CapacityNodeState:
    """Claim-time state for one capacity node; no amount is inferred here."""

    capacity_id: str
    applicability: str
    availability: str
    capacity_state: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "capacity_id", _required_text(self.capacity_id, "capacity_id"))
        object.__setattr__(
            self,
            "applicability",
            _member(self.applicability, APPLICABILITY_STATES, "applicability"),
        )
        object.__setattr__(
            self,
            "availability",
            _member(self.availability, AVAILABILITY_STATES, "availability"),
        )
        object.__setattr__(
            self,
            "capacity_state",
            _member(self.capacity_state, CAPACITY_STATES, "capacity_state"),
        )


@dataclass(frozen=True)
class CapacityOrderEvaluation:
    status: str
    selected_capacity_id: str | None
    traversed_capacity_ids: tuple[str, ...]
    unresolved_capacity_id: str | None
    reasons: tuple[str, ...]


def evaluate_next_capacity(
    *, rule: CapacityOrderRule, states: tuple[CapacityNodeState, ...]
) -> CapacityOrderEvaluation:
    """Return the first safely consumable capacity in the governed order.

    Traversal may skip a node only when its non-use is itself resolved: either the
    node is NOT_APPLICABLE, UNAVAILABLE, or EXHAUSTED. Any unresolved state blocks
    traversal because silently skipping it could violate the governed order.
    """
    if not isinstance(rule, CapacityOrderRule):
        raise CapacityOrderingContractError("rule must be CapacityOrderRule")
    if not isinstance(states, tuple):
        raise CapacityOrderingContractError("states must be a tuple")
    if not all(isinstance(state, CapacityNodeState) for state in states):
        raise CapacityOrderingContractError("states must contain CapacityNodeState values")

    by_id = {state.capacity_id: state for state in states}
    if len(by_id) != len(states):
        raise CapacityOrderingContractError("states must not contain duplicate capacity_id values")

    unknown_ids = set(by_id) - {node.capacity_id for node in rule.nodes}
    if unknown_ids:
        raise CapacityOrderingContractError(
            f"states contain capacity IDs not present in rule: {sorted(unknown_ids)}"
        )

    traversed: list[str] = []
    reasons: list[str] = []

    for node in rule.nodes:
        state = by_id.get(node.capacity_id)
        if state is None:
            return CapacityOrderEvaluation(
                status="UNRESOLVED",
                selected_capacity_id=None,
                traversed_capacity_ids=tuple(traversed),
                unresolved_capacity_id=node.capacity_id,
                reasons=(f"Missing claim-time state for {node.capacity_id}.",),
            )

        if (
            state.applicability == "UNRESOLVED"
            or state.availability == "UNRESOLVED"
            or state.capacity_state == "UNRESOLVED"
        ):
            return CapacityOrderEvaluation(
                status="UNRESOLVED",
                selected_capacity_id=None,
                traversed_capacity_ids=tuple(traversed),
                unresolved_capacity_id=node.capacity_id,
                reasons=(f"Unresolved state blocks ordered traversal at {node.capacity_id}.",),
            )

        if state.applicability == "NOT_APPLICABLE":
            traversed.append(node.capacity_id)
            reasons.append(f"{node.capacity_id} skipped: not applicable.")
            continue

        if state.availability == "UNAVAILABLE":
            traversed.append(node.capacity_id)
            reasons.append(f"{node.capacity_id} skipped: unavailable.")
            continue

        if state.capacity_state == "EXHAUSTED":
            traversed.append(node.capacity_id)
            reasons.append(f"{node.capacity_id} skipped: exhausted.")
            continue

        return CapacityOrderEvaluation(
            status="SELECTED",
            selected_capacity_id=node.capacity_id,
            traversed_capacity_ids=tuple(traversed),
            unresolved_capacity_id=None,
            reasons=tuple(reasons + [f"{node.capacity_id} selected as first consumable capacity."]),
        )

    return CapacityOrderEvaluation(
        status="NO_CAPACITY",
        selected_capacity_id=None,
        traversed_capacity_ids=tuple(traversed),
        unresolved_capacity_id=None,
        reasons=tuple(reasons + ["No consumable capacity remains in the governed sequence."]),
    )


__all__ = [
    "CapacityNodeState",
    "CapacityOrderEvaluation",
    "CapacityOrderingContractError",
    "CapacityOrderNode",
    "CapacityOrderRule",
    "evaluate_next_capacity",
]
