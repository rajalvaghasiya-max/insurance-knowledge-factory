"""Insurer-independent evaluation of bounded restoration claim-state mechanics.

This module deliberately evaluates only closed restoration semantics that can be
represented as governed parameters. It does not calculate claim payment,
discover product facts, interpret free-form expressions, or branch on insurer or
product identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


EFFECTIVE_POINTS = frozenset({"SUBSEQUENT_CLAIM_ONLY", "WITHIN_TRIGGERING_CLAIM"})
RELATIONSHIP_RULES = frozenset({"ALLOWED", "NOT_ALLOWED", "UNRESOLVED"})
ACTIVATION_TRIGGER_STATES = frozenset({"RESOLVED", "UNRESOLVED"})
CLAIM_SEQUENCE_STATES = frozenset({"TRIGGERING", "SUBSEQUENT"})
ILLNESS_RELATIONSHIPS = frozenset({"SAME", "DIFFERENT", "UNKNOWN"})
EVALUATION_STATUSES = frozenset({"ELIGIBLE", "NOT_ELIGIBLE", "UNRESOLVED"})


class RestorationStateContractError(ValueError):
    """Raised when a restoration rule or claim-state vector is invalid."""


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RestorationStateContractError(f"{label} must be non-empty text")
    return value.strip()


def _member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise RestorationStateContractError(
            f"{label} must be one of {sorted(allowed)}; got {value!r}"
        )
    return str(value)


@dataclass(frozen=True)
class RestorationFrequencyBand:
    """One closed Sum-Insured band controlling restoration recurrence."""

    min_sum_insured_rupees: int
    max_sum_insured_rupees: int | None
    restoration_count_limit: int | None

    def __post_init__(self) -> None:
        if isinstance(self.min_sum_insured_rupees, bool) or not isinstance(
            self.min_sum_insured_rupees, int
        ) or self.min_sum_insured_rupees < 0:
            raise RestorationStateContractError(
                "min_sum_insured_rupees must be a non-negative integer"
            )
        if self.max_sum_insured_rupees is not None:
            if isinstance(self.max_sum_insured_rupees, bool) or not isinstance(
                self.max_sum_insured_rupees, int
            ):
                raise RestorationStateContractError(
                    "max_sum_insured_rupees must be an integer or None"
                )
            if self.max_sum_insured_rupees < self.min_sum_insured_rupees:
                raise RestorationStateContractError(
                    "max_sum_insured_rupees cannot be below the minimum"
                )
        if self.restoration_count_limit is not None:
            if isinstance(self.restoration_count_limit, bool) or not isinstance(
                self.restoration_count_limit, int
            ) or self.restoration_count_limit < 1:
                raise RestorationStateContractError(
                    "restoration_count_limit must be a positive integer or None for unlimited"
                )

    def contains(self, sum_insured_rupees: int) -> bool:
        return sum_insured_rupees >= self.min_sum_insured_rupees and (
            self.max_sum_insured_rupees is None
            or sum_insured_rupees <= self.max_sum_insured_rupees
        )


@dataclass(frozen=True)
class RestorationRuleParameters:
    """Closed declarative parameters consumed by the generic evaluator."""

    rule_id: str
    activation_trigger_state: str
    activation_effective_point: str
    subsequent_claim_min_gap_days: int | None
    other_beneficiary_gap_exempt: bool
    same_illness_subsequent_claim_rule: str
    different_illness_subsequent_claim_rule: str
    covered_section: str
    frequency_bands: tuple[RestorationFrequencyBand, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", _required_text(self.rule_id, "rule_id"))
        object.__setattr__(
            self,
            "activation_trigger_state",
            _member(
                self.activation_trigger_state,
                ACTIVATION_TRIGGER_STATES,
                "activation_trigger_state",
            ),
        )
        object.__setattr__(
            self,
            "activation_effective_point",
            _member(
                self.activation_effective_point,
                EFFECTIVE_POINTS,
                "activation_effective_point",
            ),
        )
        if self.subsequent_claim_min_gap_days is not None:
            if isinstance(self.subsequent_claim_min_gap_days, bool) or not isinstance(
                self.subsequent_claim_min_gap_days, int
            ) or self.subsequent_claim_min_gap_days < 0:
                raise RestorationStateContractError(
                    "subsequent_claim_min_gap_days must be a non-negative integer or None"
                )
        if not isinstance(self.other_beneficiary_gap_exempt, bool):
            raise RestorationStateContractError(
                "other_beneficiary_gap_exempt must be boolean"
            )
        object.__setattr__(
            self,
            "same_illness_subsequent_claim_rule",
            _member(
                self.same_illness_subsequent_claim_rule,
                RELATIONSHIP_RULES,
                "same_illness_subsequent_claim_rule",
            ),
        )
        object.__setattr__(
            self,
            "different_illness_subsequent_claim_rule",
            _member(
                self.different_illness_subsequent_claim_rule,
                RELATIONSHIP_RULES,
                "different_illness_subsequent_claim_rule",
            ),
        )
        object.__setattr__(
            self, "covered_section", _required_text(self.covered_section, "covered_section")
        )
        if not isinstance(self.frequency_bands, tuple) or not self.frequency_bands:
            raise RestorationStateContractError("frequency_bands must be a non-empty tuple")
        if not all(isinstance(item, RestorationFrequencyBand) for item in self.frequency_bands):
            raise RestorationStateContractError(
                "frequency_bands must contain RestorationFrequencyBand values"
            )
        ordered = sorted(self.frequency_bands, key=lambda item: item.min_sum_insured_rupees)
        for previous, current in zip(ordered, ordered[1:]):
            if previous.max_sum_insured_rupees is None:
                raise RestorationStateContractError(
                    "an unbounded frequency band must be the final band"
                )
            if current.min_sum_insured_rupees <= previous.max_sum_insured_rupees:
                raise RestorationStateContractError("frequency bands must not overlap")


@dataclass(frozen=True)
class RestorationClaimState:
    """Claim-time facts supplied to the generic restoration evaluator."""

    sum_insured_rupees: int
    claim_sequence: str
    claim_section: str
    prior_restorations_used: int
    days_since_prior_discharge: int | None = None
    other_insured_beneficiary: bool = False
    illness_relationship: str = "UNKNOWN"

    def __post_init__(self) -> None:
        if isinstance(self.sum_insured_rupees, bool) or not isinstance(
            self.sum_insured_rupees, int
        ) or self.sum_insured_rupees <= 0:
            raise RestorationStateContractError(
                "sum_insured_rupees must be a positive integer"
            )
        object.__setattr__(
            self,
            "claim_sequence",
            _member(self.claim_sequence, CLAIM_SEQUENCE_STATES, "claim_sequence"),
        )
        object.__setattr__(
            self, "claim_section", _required_text(self.claim_section, "claim_section")
        )
        if isinstance(self.prior_restorations_used, bool) or not isinstance(
            self.prior_restorations_used, int
        ) or self.prior_restorations_used < 0:
            raise RestorationStateContractError(
                "prior_restorations_used must be a non-negative integer"
            )
        if self.days_since_prior_discharge is not None:
            if isinstance(self.days_since_prior_discharge, bool) or not isinstance(
                self.days_since_prior_discharge, int
            ) or self.days_since_prior_discharge < 0:
                raise RestorationStateContractError(
                    "days_since_prior_discharge must be a non-negative integer or None"
                )
        if not isinstance(self.other_insured_beneficiary, bool):
            raise RestorationStateContractError(
                "other_insured_beneficiary must be boolean"
            )
        object.__setattr__(
            self,
            "illness_relationship",
            _member(
                self.illness_relationship,
                ILLNESS_RELATIONSHIPS,
                "illness_relationship",
            ),
        )


@dataclass(frozen=True)
class RestorationEvaluationResult:
    status: str
    selected_frequency_limit: int | None
    frequency_unlimited: bool
    failed_conditions: tuple[str, ...]
    unresolved_conditions: tuple[str, ...]
    derived_reasons: tuple[str, ...]


def _frequency_band(
    rule: RestorationRuleParameters, sum_insured_rupees: int
) -> RestorationFrequencyBand | None:
    matches = tuple(
        band for band in rule.frequency_bands if band.contains(sum_insured_rupees)
    )
    if len(matches) > 1:
        raise RestorationStateContractError(
            "frequency band configuration matched more than one band"
        )
    return matches[0] if matches else None


def evaluate_restoration_state(
    *, rule: RestorationRuleParameters, state: RestorationClaimState
) -> RestorationEvaluationResult:
    """Evaluate bounded restoration usability without insurer-specific branching."""
    if not isinstance(rule, RestorationRuleParameters):
        raise RestorationStateContractError(
            "rule must be RestorationRuleParameters"
        )
    if not isinstance(state, RestorationClaimState):
        raise RestorationStateContractError("state must be RestorationClaimState")

    failed: list[str] = []
    unresolved: list[str] = []
    reasons: list[str] = []

    band = _frequency_band(rule, state.sum_insured_rupees)
    if band is None:
        unresolved.append("NO_FREQUENCY_BAND_FOR_SUM_INSURED")
        frequency_limit = None
        frequency_unlimited = False
    else:
        frequency_limit = band.restoration_count_limit
        frequency_unlimited = frequency_limit is None
        if frequency_limit is not None and state.prior_restorations_used >= frequency_limit:
            failed.append("RESTORATION_FREQUENCY_EXHAUSTED")

    if state.claim_section != rule.covered_section:
        failed.append("CLAIM_SECTION_NOT_COVERED")

    if state.claim_sequence == "TRIGGERING":
        if rule.activation_effective_point == "SUBSEQUENT_CLAIM_ONLY":
            failed.append("TRIGGERING_CLAIM_CANNOT_CONSUME_RESTORATION")
            reasons.append(
                "Derived from activation_effective_point=SUBSEQUENT_CLAIM_ONLY."
            )
    else:
        if rule.activation_trigger_state == "UNRESOLVED":
            unresolved.append("ACTIVATION_TRIGGER_UNRESOLVED")

        if rule.subsequent_claim_min_gap_days is not None and not (
            rule.other_beneficiary_gap_exempt and state.other_insured_beneficiary
        ):
            if state.days_since_prior_discharge is None:
                unresolved.append("SUBSEQUENT_CLAIM_GAP_UNRESOLVED")
            elif state.days_since_prior_discharge < rule.subsequent_claim_min_gap_days:
                failed.append("SUBSEQUENT_CLAIM_GAP_NOT_MET")

        relationship_rule = None
        if state.illness_relationship == "SAME":
            relationship_rule = rule.same_illness_subsequent_claim_rule
        elif state.illness_relationship == "DIFFERENT":
            relationship_rule = rule.different_illness_subsequent_claim_rule

        if relationship_rule == "NOT_ALLOWED":
            failed.append("ILLNESS_RELATIONSHIP_NOT_ALLOWED")
        elif relationship_rule == "UNRESOLVED":
            unresolved.append("ILLNESS_RELATIONSHIP_RULE_UNRESOLVED")
        elif state.illness_relationship == "UNKNOWN":
            unresolved.append("ILLNESS_RELATIONSHIP_UNKNOWN")

    if failed:
        status = "NOT_ELIGIBLE"
    elif unresolved:
        status = "UNRESOLVED"
    else:
        status = "ELIGIBLE"

    return RestorationEvaluationResult(
        status=_member(status, EVALUATION_STATUSES, "status"),
        selected_frequency_limit=frequency_limit,
        frequency_unlimited=frequency_unlimited,
        failed_conditions=tuple(failed),
        unresolved_conditions=tuple(unresolved),
        derived_reasons=tuple(reasons),
    )


__all__ = [
    "RestorationClaimState",
    "RestorationEvaluationResult",
    "RestorationFrequencyBand",
    "RestorationRuleParameters",
    "RestorationStateContractError",
    "evaluate_restoration_state",
]
