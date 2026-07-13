"""Deterministic explanation contract for governed financial outcomes.

This module turns an already calculated, evidence-backed financial effect into
structured explanation content. It is deliberately not an LLM prompt, advice
engine, claim-settlement decision, or recommendation layer.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

from factory_core.rules.conditional_rule_evaluation_models import (
    ApplicabilityStatus,
    RuleApplicabilityDecision,
)
from factory_core.rules.conditional_rule_models import ConditionalRule, RuleEffectValueKind
from factory_core.rules.fixed_percentage_financial_effect_evaluator import (
    FinancialEffectStatus,
    FixedPercentageFinancialEffect,
)


class OutcomeExplanationStatus(StrEnum):
    EXPLAINABLE = "explainable"
    NOT_EXPLAINABLE = "not_explainable"


@dataclass(frozen=True, slots=True)
class OutcomeExplanationPayload:
    """Structured, evidence-linked content safe for later rendering.

    The payload contains a deterministic template result, not customer advice.
    It intentionally says "may" and names the supplied *admissible* amount;
    it never claims that a claim is payable or settled.
    """

    rule_id: str
    status: OutcomeExplanationStatus
    headline: str | None
    summary: str | None
    calculation: str | None
    condition_labels: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    caveats: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("OutcomeExplanationPayload.rule_id must not be blank.")
        if self.status is OutcomeExplanationStatus.EXPLAINABLE:
            if not self.headline or not self.summary or not self.calculation:
                raise ValueError("Explainable payload requires headline, summary, and calculation.")
            if not self.evidence_ids:
                raise ValueError("Explainable payload requires at least one evidence ID.")
            if self.blocking_reasons:
                raise ValueError("Explainable payload cannot carry blocking reasons.")
        else:
            if any(value is not None for value in (self.headline, self.summary, self.calculation)):
                raise ValueError("Non-explainable payload must not expose financial explanation text.")
            if not self.blocking_reasons:
                raise ValueError("Non-explainable payload requires a blocking reason.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "status": self.status.value,
            "headline": self.headline,
            "summary": self.summary,
            "calculation": self.calculation,
            "condition_labels": list(self.condition_labels),
            "evidence_ids": list(self.evidence_ids),
            "caveats": list(self.caveats),
            "blocking_reasons": list(self.blocking_reasons),
        }


class FinancialOutcomeExplanationBuilder:
    """Build deterministic explanation payloads for calculated fixed percentages only."""

    builder_id = "factory_core.financial_outcome_explanation_builder"
    builder_version = "1.0"

    def build(
        self,
        rule: ConditionalRule,
        applicability: RuleApplicabilityDecision,
        effect: FixedPercentageFinancialEffect,
    ) -> OutcomeExplanationPayload:
        self._validate_identity(rule, applicability, effect)
        if applicability.status is not ApplicabilityStatus.APPLIES:
            return self._blocked(rule.rule_id, "The rule is not deterministically applicable to this scenario.")
        if effect.status is not FinancialEffectStatus.CALCULATED:
            return self._blocked(rule.rule_id, *(effect.reasons or ("The financial effect is not calculable.",)))
        if rule.effect.value_kind is not RuleEffectValueKind.FIXED:
            return self._blocked(rule.rule_id, "Selectable or non-fixed values require a separate selection step.")
        if not self._is_supported_effect(rule):
            return self._blocked(rule.rule_id, "The rule effect is outside the fixed-percentage explanation contract.")
        if any(value is None for value in (
            effect.admissible_claim_amount,
            effect.insured_share_amount,
            effect.insurer_share_amount,
            effect.applied_percentage,
        )):
            return self._blocked(rule.rule_id, "The calculated financial effect is incomplete.")

        evidence_ids = (rule.evidence.primary.evidence_id,) + tuple(
            item.evidence_id for item in rule.evidence.corroborating
        )
        condition_labels = tuple(
            f"{predicate.dimension} = {predicate.value}"
            for predicate in (*rule.applies_when, *rule.coverage_scope)
        )
        pct = _format_number(effect.applied_percentage)
        amount = _inr(effect.admissible_claim_amount)
        insured = _inr(effect.insured_share_amount)
        insurer = _inr(effect.insurer_share_amount)
        return OutcomeExplanationPayload(
            rule_id=rule.rule_id,
            status=OutcomeExplanationStatus.EXPLAINABLE,
            headline="Estimated cost share for this admissible claim amount",
            summary=(
                f"This rule applies to the supplied scenario. You may bear {pct}% "
                "of the admissible claim amount under this policy rule."
            ),
            calculation=(
                f"Using an admissible claim amount of {amount}, your estimated share is {insured}; "
                f"the insurer share under this rule is {insurer}."
            ),
            condition_labels=condition_labels,
            evidence_ids=evidence_ids,
            caveats=(
                "This is a rule-level illustration based on the supplied admissible amount.",
                "It is not a claim-admissibility, claim-settlement, or payment decision.",
            ),
        )

    @staticmethod
    def _validate_identity(
        rule: ConditionalRule,
        applicability: RuleApplicabilityDecision,
        effect: FixedPercentageFinancialEffect,
    ) -> None:
        if applicability.rule_id != rule.rule_id or effect.rule_id != rule.rule_id:
            raise ValueError("Rule, applicability decision, and financial effect must share the same rule_id.")

    @staticmethod
    def _is_supported_effect(rule: ConditionalRule) -> bool:
        return (
            rule.effect.operator == "insured_bears_percentage"
            and rule.effect.unit == "percent"
            and rule.effect.basis == "admissible_claim_amount"
        )

    @staticmethod
    def _blocked(rule_id: str, *reasons: str) -> OutcomeExplanationPayload:
        return OutcomeExplanationPayload(
            rule_id=rule_id,
            status=OutcomeExplanationStatus.NOT_EXPLAINABLE,
            headline=None,
            summary=None,
            calculation=None,
            condition_labels=(),
            evidence_ids=(),
            blocking_reasons=tuple(reasons),
        )


def build_financial_outcome_explanation(
    rule: ConditionalRule,
    applicability: RuleApplicabilityDecision,
    effect: FixedPercentageFinancialEffect,
) -> OutcomeExplanationPayload:
    return FinancialOutcomeExplanationBuilder().build(rule, applicability, effect)


def _inr(value: Decimal) -> str:
    return f"₹{value:,.2f}"


def _format_number(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"
