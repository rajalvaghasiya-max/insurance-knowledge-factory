"""Read-only Health orchestration for authoritative copay applicability.

This harness composes published-rule resolution, strict Health normalization,
scenario-semantics review, and generic predicate evaluation. It does not rewrite
published artifacts, choose voluntary copay values, calculate money, or generate advice.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from factory_core.rules.conditional_rule_applicability_evaluator import ConditionalRuleApplicabilityEvaluator
from factory_core.rules.conditional_rule_evaluation_models import ApplicabilityStatus, RuleApplicabilityDecision
from factory_core.rules.conditional_rule_models import (
    ConditionOperator, ConditionalRule, EvidenceReference, RuleAssemblyStatus,
    RuleEffect, RuleEffectValueKind, RuleEvidence, RulePredicate,
)
from factory_core.rules.conditional_rule_resolver import ConditionalRuleQuery, ConditionalRuleResolver
from knowledge_domains.health.scenario_normalization import (
    HealthScenarioNormalizationResult, ScenarioNormalizationStatus, normalize_health_scenario,
)
from knowledge_domains.health.scenario_scope_semantics import (
    ScenarioPredicateRole, review_health_rule_scenario_semantics,
)

@dataclass(frozen=True, slots=True)
class CopayApplicabilityItem:
    rule_id: str
    decision: RuleApplicabilityDecision
    excluded_metadata_predicates: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class CopayApplicabilityHarnessResult:
    normalization: HealthScenarioNormalizationResult
    items: tuple[CopayApplicabilityItem, ...] = ()

    @property
    def applicable_rule_ids(self) -> tuple[str, ...]:
        return tuple(i.rule_id for i in self.items if i.decision.status is ApplicabilityStatus.APPLIES)


def evaluate_authoritative_copay_applicability(*, artifact_path: str | Path, scenario_id: str,
    entity_id: str, raw_inputs: Mapping[str, Any]) -> CopayApplicabilityHarnessResult:
    """Evaluate all resolved authoritative copay rules against one normalized scenario."""
    normalization = normalize_health_scenario(scenario_id=scenario_id, entity_id=entity_id, raw_inputs=raw_inputs)
    if normalization.status is not ScenarioNormalizationStatus.NORMALIZED:
        return CopayApplicabilityHarnessResult(normalization=normalization)
    assert normalization.scenario is not None
    resolved = ConditionalRuleResolver().resolve(artifact_path, ConditionalRuleQuery(entity_id=entity_id, concept_id="copay"))
    evaluator = ConditionalRuleApplicabilityEvaluator()
    items=[]
    for payload in resolved.rules:
        rule = _rule_from_mapping(payload)
        projection, excluded = _scenario_facing_projection(rule)
        # Unknown semantics are fail-closed: no applicability determination.
        review = review_health_rule_scenario_semantics(rule)
        if review.has_unreviewed_predicates:
            decision = RuleApplicabilityDecision(rule_id=rule.rule_id, status=ApplicabilityStatus.INDETERMINATE,
                reasons=("A declared scope predicate has no reviewed scenario-facing semantics.",))
        else:
            decision = evaluator.evaluate(projection, normalization.scenario)
        items.append(CopayApplicabilityItem(rule_id=rule.rule_id, decision=decision, excluded_metadata_predicates=excluded))
    return CopayApplicabilityHarnessResult(normalization=normalization, items=tuple(items))


def _scenario_facing_projection(rule: ConditionalRule) -> tuple[ConditionalRule, tuple[str, ...]]:
    review = review_health_rule_scenario_semantics(rule)
    retained=[]; excluded=[]
    for predicate, assessment in zip(rule.coverage_scope, review.coverage_scope, strict=True):
        if assessment.role is ScenarioPredicateRole.RULE_METADATA_ONLY:
            excluded.append(f"{predicate.dimension}={predicate.value}")
        else:
            retained.append(predicate)
    return replace(rule, coverage_scope=tuple(retained)), tuple(excluded)


def _predicate(payload: Mapping[str, Any]) -> RulePredicate:
    value=payload["value"]
    if payload["operator"] == "in" and isinstance(value, list): value=tuple(value)
    return RulePredicate(str(payload["dimension"]), ConditionOperator(payload["operator"]), value)

def _evidence(payload: Mapping[str, Any]) -> EvidenceReference:
    return EvidenceReference(payload["evidence_id"], payload["document_id"], payload["document_type"], int(payload["authority_score"]),
        fragment_id=payload.get("fragment_id"), source_char_range=payload.get("source_char_range"), corroboration_role=payload.get("corroboration_role"))

def _rule_from_mapping(payload: Mapping[str, Any]) -> ConditionalRule:
    effect=payload["effect"]; value=effect["value"]
    kind=RuleEffectValueKind(effect.get("value_kind", "fixed"))
    if kind is RuleEffectValueKind.ALLOWED_SET and isinstance(value, list): value=tuple(value)
    ev=payload["evidence"]
    return ConditionalRule(rule_id=payload["rule_id"], concept_id=payload["concept_id"], rule_type=payload["rule_type"],
        effect=RuleEffect(effect["operator"], value, effect.get("unit"), effect.get("basis"), kind),
        applies_when=tuple(_predicate(x) for x in payload["applies_when"]),
        coverage_scope=tuple(_predicate(x) for x in payload["coverage_scope"]),
        evidence=RuleEvidence(_evidence(ev["primary_evidence"]), tuple(_evidence(x) for x in ev.get("corroborating_evidence", []))),
        status=RuleAssemblyStatus(payload["status"]), unresolved_ambiguities=tuple(payload.get("unresolved_ambiguities", [])), assembly_key=payload.get("assembly_key"))
