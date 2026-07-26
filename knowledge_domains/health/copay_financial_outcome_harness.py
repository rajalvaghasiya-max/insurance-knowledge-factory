"""Read-only Health orchestration for governed copay financial outcomes.

This harness composes the authoritative copay applicability harness with the
fixed-percentage financial effect evaluator.  It is intentionally not a claim
settlement engine: callers must provide an explicit admissible claim amount;
allowed-set voluntary copay values are never selected automatically.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from factory_core.rules.conditional_rule_evaluation_models import ApplicabilityStatus
from factory_core.rules.conditional_rule_resolver import ConditionalRuleQuery, ConditionalRuleResolver
from factory_core.rules.fixed_percentage_financial_effect_evaluator import (
    FinancialEffectStatus,
    FixedPercentageFinancialEffect,
    FixedPercentageFinancialEffectEvaluator,
)
from knowledge_domains.health.copay_applicability_harness import (
    CopayApplicabilityHarnessResult,
    _rule_from_mapping,
    evaluate_authoritative_copay_applicability,
)


@dataclass(frozen=True, slots=True)
class CopayFinancialOutcomeItem:
    """One rule's applicability and, only where permitted, its arithmetic result."""

    rule_id: str
    applicability_status: ApplicabilityStatus
    financial_effect: FixedPercentageFinancialEffect | None
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CopayFinancialOutcomeHarnessResult:
    """Combined read-only trace for rule applicability and narrow financial effect."""

    applicability: CopayApplicabilityHarnessResult
    items: tuple[CopayFinancialOutcomeItem, ...]

    @property
    def calculated_rule_ids(self) -> tuple[str, ...]:
        return tuple(
            item.rule_id
            for item in self.items
            if item.financial_effect is not None
            and item.financial_effect.status is FinancialEffectStatus.CALCULATED
        )


def evaluate_authoritative_copay_financial_outcome(
    *,
    artifact_path: str | Path,
    scenario_id: str,
    entity_id: str,
    raw_inputs: Mapping[str, Any],
    admissible_claim_amount: Decimal | int | float | str | None,
) -> CopayFinancialOutcomeHarnessResult:
    """Evaluate published copay rules then calculate eligible fixed-percentage effects.

    All resolved rules are retained in the trace. Non-applicable and
    indeterminate rules deliberately have no financial effect. An applicable
    allowed-set effect is passed to the financial evaluator, which returns an
    explicit ``not_calculable`` result rather than selecting a percentage.
    """
    applicability = evaluate_authoritative_copay_applicability(
        artifact_path=artifact_path,
        scenario_id=scenario_id,
        entity_id=entity_id,
        raw_inputs=raw_inputs,
    )
    if applicability.normalization.scenario is None:
        return CopayFinancialOutcomeHarnessResult(applicability=applicability, items=())

    resolved = ConditionalRuleResolver().resolve(
        artifact_path,
        ConditionalRuleQuery(entity_id=entity_id, concept_id="copay"),
    )
    rules_by_id = {payload["rule_id"]: _rule_from_mapping(payload) for payload in resolved.rules}
    evaluator = FixedPercentageFinancialEffectEvaluator()
    items: list[CopayFinancialOutcomeItem] = []

    for applicability_item in applicability.items:
        decision = applicability_item.decision
        if decision.status is not ApplicabilityStatus.APPLIES:
            items.append(
                CopayFinancialOutcomeItem(
                    rule_id=decision.rule_id,
                    applicability_status=decision.status,
                    financial_effect=None,
                    reasons=decision.reasons,
                )
            )
            continue
        rule = rules_by_id[decision.rule_id]
        effect = evaluator.evaluate(rule, decision, admissible_claim_amount)
        items.append(
            CopayFinancialOutcomeItem(
                rule_id=decision.rule_id,
                applicability_status=decision.status,
                financial_effect=effect,
                reasons=effect.reasons,
            )
        )

    return CopayFinancialOutcomeHarnessResult(applicability=applicability, items=tuple(items))
