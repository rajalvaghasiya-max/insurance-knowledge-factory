"""Deterministic applicability evaluation for authoritative conditional rules.

This module evaluates declared rule predicates against normalized scenario inputs.
It deliberately does not select values from allowed-set effects, calculate money,
load artifacts, or create customer-facing advice.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from factory_core.rules.conditional_rule_evaluation_models import (
    ApplicabilityStatus,
    EvaluationScenario,
    PredicateAssessment,
    PredicateAssessmentStatus,
    RuleApplicabilityDecision,
)
from factory_core.rules.conditional_rule_models import (
    ConditionOperator,
    ConditionalRule,
    RuleAssemblyStatus,
    RulePredicate,
)


@dataclass(frozen=True, slots=True)
class ConditionalRuleApplicabilityEvaluator:
    """Read-only evaluator for published, unambiguous ConditionalRule objects."""

    evaluator_id: str = "factory_core.conditional_rule_applicability_evaluator"
    evaluator_version: str = "1.0"

    def evaluate(
        self,
        rule: ConditionalRule,
        scenario: EvaluationScenario,
    ) -> RuleApplicabilityDecision:
        """Return applies, does_not_apply, or indeterminate with a full trace.

        All declared ``applies_when`` and ``coverage_scope`` predicates are
        conjunctive. A known mismatch is decisive. If no mismatch exists but an
        input is missing or an operator/value pair cannot be evaluated, the
        result is indeterminate.
        """
        self._validate_rule(rule)
        assessments = tuple(
            self._assess(predicate, scenario) for predicate in (*rule.applies_when, *rule.coverage_scope)
        )
        statuses = {assessment.status for assessment in assessments}

        if PredicateAssessmentStatus.MISMATCHED in statuses:
            return RuleApplicabilityDecision(
                rule_id=rule.rule_id,
                status=ApplicabilityStatus.DOES_NOT_APPLY,
                predicate_assessments=assessments,
                reasons=("At least one declared rule predicate does not match the scenario.",),
            )
        if (
            PredicateAssessmentStatus.MISSING_SCENARIO_INPUT in statuses
            or PredicateAssessmentStatus.UNSUPPORTED_OPERATOR in statuses
        ):
            return RuleApplicabilityDecision(
                rule_id=rule.rule_id,
                status=ApplicabilityStatus.INDETERMINATE,
                predicate_assessments=assessments,
                reasons=("The scenario cannot deterministically evaluate every declared rule predicate.",),
            )
        return RuleApplicabilityDecision(
            rule_id=rule.rule_id,
            status=ApplicabilityStatus.APPLIES,
            predicate_assessments=assessments,
            reasons=(),
        )

    @staticmethod
    def _validate_rule(rule: ConditionalRule) -> None:
        if rule.status is not RuleAssemblyStatus.EVIDENCE_ASSEMBLED_NOT_FACT_EXTRACTED:
            raise ValueError("Applicability evaluation accepts only evidence-assembled authoritative rules.")
        if rule.unresolved_ambiguities:
            raise ValueError("Applicability evaluation rejects rules with unresolved ambiguities.")

    @staticmethod
    def _assess(predicate: RulePredicate, scenario: EvaluationScenario) -> PredicateAssessment:
        if predicate.dimension not in scenario.inputs:
            return PredicateAssessment(
                dimension=predicate.dimension,
                operator=predicate.operator.value,
                expected_value=predicate.value,
                status=PredicateAssessmentStatus.MISSING_SCENARIO_INPUT,
                scenario_value_present=False,
            )

        actual = scenario.inputs[predicate.dimension]
        try:
            matched = _matches(predicate.operator, actual, predicate.value)
        except (TypeError, ValueError):
            return PredicateAssessment(
                dimension=predicate.dimension,
                operator=predicate.operator.value,
                expected_value=predicate.value,
                status=PredicateAssessmentStatus.UNSUPPORTED_OPERATOR,
                scenario_value_present=True,
            )

        return PredicateAssessment(
            dimension=predicate.dimension,
            operator=predicate.operator.value,
            expected_value=predicate.value,
            status=(PredicateAssessmentStatus.MATCHED if matched else PredicateAssessmentStatus.MISMATCHED),
            scenario_value_present=True,
        )


def evaluate_rule_applicability(
    rule: ConditionalRule,
    scenario: EvaluationScenario,
) -> RuleApplicabilityDecision:
    """Convenience function for callers that do not need a configured evaluator."""
    return ConditionalRuleApplicabilityEvaluator().evaluate(rule, scenario)


def _matches(operator: ConditionOperator, actual: Any, expected: Any) -> bool:
    if operator is ConditionOperator.EQUALS:
        return actual == expected
    if operator is ConditionOperator.NOT_EQUALS:
        return actual != expected
    if operator is ConditionOperator.IN:
        return actual in expected
    if operator is ConditionOperator.GREATER_THAN_OR_EQUAL:
        return actual >= expected
    if operator is ConditionOperator.LESS_THAN_OR_EQUAL:
        return actual <= expected
    raise ValueError(f"Unsupported rule predicate operator: {operator!r}")
