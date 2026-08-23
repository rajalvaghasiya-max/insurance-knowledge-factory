"""Typed semantics for explicit conditional co-payment non-application.

This contract is intentionally distinct from a percentage-bearing co-payment obligation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CopaymentNonapplicationContractError(ValueError):
    """Raised when an explicit co-payment non-application rule is invalid."""


class CopaymentNonapplicationEffect(str, Enum):
    DOES_NOT_APPLY = "DOES_NOT_APPLY"


@dataclass(frozen=True)
class ConditionalCopaymentNonapplication:
    trigger_condition: str
    applicability_scope: str
    evidence_reference_ids: tuple[str, ...]
    effect: CopaymentNonapplicationEffect = CopaymentNonapplicationEffect.DOES_NOT_APPLY

    def __post_init__(self) -> None:
        if not isinstance(self.trigger_condition, str) or not self.trigger_condition.strip():
            raise CopaymentNonapplicationContractError("trigger_condition must be non-empty")
        if not isinstance(self.applicability_scope, str) or not self.applicability_scope.strip():
            raise CopaymentNonapplicationContractError("applicability_scope must be non-empty")
        if not self.evidence_reference_ids or not all(
            isinstance(item, str) and item.strip() for item in self.evidence_reference_ids
        ):
            raise CopaymentNonapplicationContractError(
                "explicit co-payment non-application requires evidence"
            )
        if self.effect is not CopaymentNonapplicationEffect.DOES_NOT_APPLY:
            raise CopaymentNonapplicationContractError(
                "explicit co-payment non-application effect must be DOES_NOT_APPLY"
            )


__all__ = [
    "ConditionalCopaymentNonapplication",
    "CopaymentNonapplicationContractError",
    "CopaymentNonapplicationEffect",
]
