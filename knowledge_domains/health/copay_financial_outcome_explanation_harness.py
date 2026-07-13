"""Read-only Health orchestration for explained copay financial outcomes.

This harness composes the governed financial-outcome harness with the
deterministic explanation contract. It does not mutate artifacts, select
voluntary copay options, decide claim admissibility, or generate advice.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from factory_core.rules.conditional_rule_models import ConditionalRule
from factory_core.rules.conditional_rule_resolver import ConditionalRuleQuery, ConditionalRuleResolver
from factory_core.rules.financial_outcome_explanation_contract import (
    FinancialOutcomeExplanationBuilder,
    OutcomeExplanationPayload,
    OutcomeExplanationStatus,
)
from knowledge_domains.health.copay_applicability_harness import _rule_from_mapping
from knowledge_domains.health.copay_financial_outcome_harness import (
    CopayFinancialOutcomeHarnessResult,
    evaluate_authoritative_copay_financial_outcome,
)


@dataclass(frozen=True, slots=True)
class CopayExplainedFinancialOutcomeItem:
    """One rule outcome paired with safe explanation content or a block reason."""

    rule_id: str
    explanation: OutcomeExplanationPayload


@dataclass(frozen=True, slots=True)
class CopayExplainedFinancialOutcomeHarnessResult:
    """End-to-end read-only trace from raw scenario to structured explanation."""

    financial_outcome: CopayFinancialOutcomeHarnessResult
    items: tuple[CopayExplainedFinancialOutcomeItem, ...] = ()

    @property
    def explainable_rule_ids(self) -> tuple[str, ...]:
        return tuple(
            item.rule_id
            for item in self.items
            if item.explanation.status is OutcomeExplanationStatus.EXPLAINABLE
        )


def evaluate_authoritative_copay_financial_outcome_explanation(
    *,
    artifact_path: str | Path,
    scenario_id: str,
    entity_id: str,
    raw_inputs: Mapping[str, Any],
    admissible_claim_amount: Decimal | int | float | str | None,
) -> CopayExplainedFinancialOutcomeHarnessResult:
    """Produce deterministic explanation payloads for all resolved copay rules.

    Rules without a calculated effect intentionally yield ``not_explainable``.
    This includes non-applicable/indeterminate cases and selectable voluntary
    copay percentages, for which the financial evaluator records a reason.
    """
    financial_outcome = evaluate_authoritative_copay_financial_outcome(
        artifact_path=artifact_path,
        scenario_id=scenario_id,
        entity_id=entity_id,
        raw_inputs=raw_inputs,
        admissible_claim_amount=admissible_claim_amount,
    )
    if financial_outcome.applicability.normalization.scenario is None:
        return CopayExplainedFinancialOutcomeHarnessResult(financial_outcome=financial_outcome)

    resolved = ConditionalRuleResolver().resolve(
        artifact_path,
        ConditionalRuleQuery(entity_id=entity_id, concept_id="copay"),
    )
    rules_by_id: dict[str, ConditionalRule] = {
        payload["rule_id"]: _rule_from_mapping(payload) for payload in resolved.rules
    }
    builder = FinancialOutcomeExplanationBuilder()
    items: list[CopayExplainedFinancialOutcomeItem] = []

    for outcome_item in financial_outcome.items:
        rule = rules_by_id[outcome_item.rule_id]
        applicability_item = next(
            item
            for item in financial_outcome.applicability.items
            if item.rule_id == outcome_item.rule_id
        )
        if outcome_item.financial_effect is None:
            explanation = _blocked(
                rule.rule_id,
                *(outcome_item.reasons or ("No governed financial effect was calculated for this rule.",)),
            )
        else:
            explanation = builder.build(rule, applicability_item.decision, outcome_item.financial_effect)
        items.append(CopayExplainedFinancialOutcomeItem(rule_id=rule.rule_id, explanation=explanation))

    return CopayExplainedFinancialOutcomeHarnessResult(
        financial_outcome=financial_outcome,
        items=tuple(items),
    )


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
