"""Narrow, deterministic financial effect evaluation for fixed percentage rules.

This module calculates only the arithmetic consequence of one applicable,
evidence-assembled rule whose effect is a fixed insured-bears percentage of an
explicitly supplied admissible claim amount. It is not a claim settlement
engine: it does not determine admissibility, aggregate rules, apply caps or
deductibles, select values from option sets, or generate advice.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import StrEnum
from typing import Any

from factory_core.rules.conditional_rule_evaluation_models import (
    ApplicabilityStatus,
    RuleApplicabilityDecision,
)
from factory_core.rules.conditional_rule_models import (
    ConditionalRule,
    RuleAssemblyStatus,
    RuleEffectValueKind,
)


class FinancialEffectStatus(StrEnum):
    CALCULATED = "calculated"
    NOT_CALCULABLE = "not_calculable"


@dataclass(frozen=True, slots=True)
class FixedPercentageFinancialEffect:
    """Non-settlement arithmetic result with an explicit reason when blocked."""

    rule_id: str
    status: FinancialEffectStatus
    admissible_claim_amount: Decimal | None
    insured_share_amount: Decimal | None
    insurer_share_amount: Decimal | None
    applied_percentage: Decimal | None
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("FixedPercentageFinancialEffect.rule_id must not be blank.")
        values = (
            self.admissible_claim_amount,
            self.insured_share_amount,
            self.insurer_share_amount,
            self.applied_percentage,
        )
        if self.status is FinancialEffectStatus.CALCULATED:
            if any(value is None for value in values):
                raise ValueError("Calculated result requires all financial values.")
            if self.reasons:
                raise ValueError("Calculated result cannot carry blocking reasons.")
        elif any(value is not None for value in (self.insured_share_amount, self.insurer_share_amount)):
            raise ValueError("Non-calculable result must not expose share amounts.")

    def to_dict(self) -> dict[str, Any]:
        def render(value: Decimal | None) -> str | None:
            return None if value is None else format(value, ".2f")
        return {
            "rule_id": self.rule_id,
            "status": self.status.value,
            "admissible_claim_amount": render(self.admissible_claim_amount),
            "insured_share_amount": render(self.insured_share_amount),
            "insurer_share_amount": render(self.insurer_share_amount),
            "applied_percentage": render(self.applied_percentage),
            "reasons": list(self.reasons),
        }


class FixedPercentageFinancialEffectEvaluator:
    """Evaluate only one fixed, percentage-based, applicable rule."""

    evaluator_id = "factory_core.fixed_percentage_financial_effect_evaluator"
    evaluator_version = "1.0"

    def evaluate(
        self,
        rule: ConditionalRule,
        applicability: RuleApplicabilityDecision,
        admissible_claim_amount: Decimal | int | float | str | None,
    ) -> FixedPercentageFinancialEffect:
        if rule.status is not RuleAssemblyStatus.EVIDENCE_ASSEMBLED_NOT_FACT_EXTRACTED:
            raise ValueError("Financial effect evaluation accepts only evidence-assembled rules.")
        if rule.unresolved_ambiguities:
            raise ValueError("Financial effect evaluation rejects unresolved rule ambiguities.")
        if applicability.rule_id != rule.rule_id:
            raise ValueError("Applicability decision must belong to the evaluated rule.")
        if applicability.status is not ApplicabilityStatus.APPLIES:
            return self._blocked(rule.rule_id, "Rule is not deterministically applicable to the scenario.")
        if rule.effect.value_kind is not RuleEffectValueKind.FIXED:
            return self._blocked(rule.rule_id, "Selectable or non-fixed effect values require a separate selection step.")
        if not (
            rule.effect.operator == "insured_bears_percentage"
            and rule.effect.unit == "percent"
            and rule.effect.basis == "admissible_claim_amount"
        ):
            return self._blocked(rule.rule_id, "Rule effect is outside the fixed-percentage admissible-amount contract.")
        percentage = _decimal(rule.effect.value)
        amount = _decimal(admissible_claim_amount)
        if percentage is None or percentage < Decimal("0") or percentage > Decimal("100"):
            return self._blocked(rule.rule_id, "Rule percentage must be a fixed number from 0 to 100.")
        if amount is None or amount <= Decimal("0"):
            return self._blocked(rule.rule_id, "Admissible claim amount must be a positive explicit amount.")

        money = Decimal("0.01")
        insured = (amount * percentage / Decimal("100")).quantize(money, rounding=ROUND_HALF_UP)
        insurer = (amount - insured).quantize(money, rounding=ROUND_HALF_UP)
        return FixedPercentageFinancialEffect(
            rule_id=rule.rule_id,
            status=FinancialEffectStatus.CALCULATED,
            admissible_claim_amount=amount.quantize(money, rounding=ROUND_HALF_UP),
            insured_share_amount=insured,
            insurer_share_amount=insurer,
            applied_percentage=percentage,
        )

    @staticmethod
    def _blocked(rule_id: str, reason: str) -> FixedPercentageFinancialEffect:
        return FixedPercentageFinancialEffect(
            rule_id=rule_id,
            status=FinancialEffectStatus.NOT_CALCULABLE,
            admissible_claim_amount=None,
            insured_share_amount=None,
            insurer_share_amount=None,
            applied_percentage=None,
            reasons=(reason,),
        )


def evaluate_fixed_percentage_financial_effect(
    rule: ConditionalRule,
    applicability: RuleApplicabilityDecision,
    admissible_claim_amount: Decimal | int | float | str | None,
) -> FixedPercentageFinancialEffect:
    return FixedPercentageFinancialEffectEvaluator().evaluate(rule, applicability, admissible_claim_amount)


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None
