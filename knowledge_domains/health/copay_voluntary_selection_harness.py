"""Read-only voluntary-copay evaluation and explanation harness.

This module composes authoritative-rule resolution, scenario applicability,
explicit allowed-set selection validation, an ephemeral fixed-value projection,
fixed-percentage arithmetic, and deterministic explanation.  It never mutates
or republishes the authoritative allowed-set rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from factory_core.rules.conditional_rule_evaluation_models import ApplicabilityStatus
from factory_core.rules.conditional_rule_models import ConditionalRule, RuleEffectValueKind
from factory_core.rules.conditional_rule_resolver import ConditionalRuleQuery, ConditionalRuleResolver
from factory_core.rules.financial_outcome_explanation_contract import (
    FinancialOutcomeExplanationBuilder,
    OutcomeExplanationPayload,
    OutcomeExplanationStatus,
)
from factory_core.rules.fixed_percentage_financial_effect_evaluator import (
    FixedPercentageFinancialEffect,
    FixedPercentageFinancialEffectEvaluator,
)
from factory_core.rules.rule_effect_selection import (
    RuleEffectSelection,
    RuleEffectSelectionSource,
    RuleEffectSelectionStatus,
    RuleEffectSelectionValidator,
    SelectedRuleForEvaluation,
    build_selected_rule_for_evaluation,
)
from knowledge_domains.health.copay_applicability_harness import (
    CopayApplicabilityHarnessResult,
    _rule_from_mapping,
    evaluate_authoritative_copay_applicability,
)


@dataclass(frozen=True, slots=True)
class VoluntaryCopayEvaluationItem:
    """Trace for one applicable authoritative allowed-set copay rule."""

    source_rule_id: str
    applicability_status: ApplicabilityStatus
    selection: RuleEffectSelection
    selected_projection: SelectedRuleForEvaluation | None
    financial_effect: FixedPercentageFinancialEffect | None
    explanation: OutcomeExplanationPayload


@dataclass(frozen=True, slots=True)
class VoluntaryCopayEvaluationHarnessResult:
    """Read-only combined trace for voluntary-copay selection and outcome."""

    applicability: CopayApplicabilityHarnessResult
    items: tuple[VoluntaryCopayEvaluationItem, ...] = ()

    @property
    def explainable_rule_ids(self) -> tuple[str, ...]:
        return tuple(
            item.source_rule_id
            for item in self.items
            if item.explanation.status is OutcomeExplanationStatus.EXPLAINABLE
        )


def evaluate_authoritative_voluntary_copay(
    *,
    artifact_path: str | Path,
    scenario_id: str,
    entity_id: str,
    raw_inputs: Mapping[str, Any],
    selected_value: Decimal | int | float | str | None,
    selection_source: RuleEffectSelectionSource,
    selection_source_reference_id: str,
    admissible_claim_amount: Decimal | int | float | str | None,
) -> VoluntaryCopayEvaluationHarnessResult:
    """Evaluate an explicitly selected voluntary copay option.

    Only authoritative allowed-set rules that deterministically apply to the
    normalized scenario are eligible. A rejected or missing selection yields a
    non-explainable result and never reaches the financial evaluator.
    """
    applicability = evaluate_authoritative_copay_applicability(
        artifact_path=artifact_path,
        scenario_id=scenario_id,
        entity_id=entity_id,
        raw_inputs=raw_inputs,
    )
    if applicability.normalization.scenario is None:
        return VoluntaryCopayEvaluationHarnessResult(applicability=applicability)

    resolved = ConditionalRuleResolver().resolve(
        artifact_path,
        ConditionalRuleQuery(entity_id=entity_id, concept_id="copay"),
    )
    rules_by_id: dict[str, ConditionalRule] = {
        payload["rule_id"]: _rule_from_mapping(payload) for payload in resolved.rules
    }
    validator = RuleEffectSelectionValidator()
    financial_evaluator = FixedPercentageFinancialEffectEvaluator()
    explanation_builder = FinancialOutcomeExplanationBuilder()
    items: list[VoluntaryCopayEvaluationItem] = []

    for applicability_item in applicability.items:
        decision = applicability_item.decision
        if decision.status is not ApplicabilityStatus.APPLIES:
            continue
        rule = rules_by_id[decision.rule_id]
        if rule.effect.value_kind is not RuleEffectValueKind.ALLOWED_SET:
            continue

        selection = validator.validate(
            rule,
            selected_value,
            source=selection_source,
            source_reference_id=selection_source_reference_id,
        )
        if selection.status is not RuleEffectSelectionStatus.SELECTED:
            items.append(
                VoluntaryCopayEvaluationItem(
                    source_rule_id=rule.rule_id,
                    applicability_status=decision.status,
                    selection=selection,
                    selected_projection=None,
                    financial_effect=None,
                    explanation=_blocked(rule.rule_id, *selection.reasons),
                )
            )
            continue

        projection = build_selected_rule_for_evaluation(rule, selection)
        effect = financial_evaluator.evaluate(
            projection.evaluation_rule,
            decision,
            admissible_claim_amount,
        )
        explanation = explanation_builder.build(
            projection.evaluation_rule,
            decision,
            effect,
        )
        items.append(
            VoluntaryCopayEvaluationItem(
                source_rule_id=rule.rule_id,
                applicability_status=decision.status,
                selection=selection,
                selected_projection=projection,
                financial_effect=effect,
                explanation=explanation,
            )
        )

    return VoluntaryCopayEvaluationHarnessResult(
        applicability=applicability,
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
        blocking_reasons=tuple(reasons) or ("No governed voluntary copay outcome was calculated.",),
    )
