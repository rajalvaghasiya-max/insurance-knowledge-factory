"""Evidence-grounded room-rent eligibility evaluation for Health policies.

This module is deliberately limited to category entitlement and an explicit ICU
exception. It does not calculate room-rent caps, proportionate deductions,
monetary loss, or claim payment.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping

from factory_core.rules.conditional_rule_resolver import (
    ConditionalRuleQuery,
    ConditionalRuleResolver,
)
from knowledge_domains.health.room_category_taxonomy import (
    RoomCategory,
    RoomCategoryAssessment,
    RoomEligibilityStatus,
    assess_room_category_eligibility,
    normalize_room_category,
)


class RoomRentEligibilityStatus(StrEnum):
    """Safe outcome states for the initial room-rent eligibility capability."""

    WITHIN_ENTITLEMENT = "within_entitlement"
    POTENTIALLY_ABOVE_ENTITLEMENT = "potentially_above_entitlement"
    ICU_EXCEPTION_APPLIES = "icu_exception_applies"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class RoomRentEligibilityDecision:
    """Read-only outcome with evidence lineage and no financial calculation."""

    scenario_id: str
    entity_id: str
    status: RoomRentEligibilityStatus
    rule_ids: tuple[str, ...]
    primary_evidence_ids: tuple[str, ...]
    reason: str
    category_assessment: RoomCategoryAssessment | None = None

    @property
    def is_explainable(self) -> bool:
        return self.status is not RoomRentEligibilityStatus.INDETERMINATE

    def to_dict(self) -> dict[str, Any]:
        assessment = self.category_assessment
        return {
            "scenario_id": self.scenario_id,
            "entity_id": self.entity_id,
            "status": self.status.value,
            "rule_ids": list(self.rule_ids),
            "primary_evidence_ids": list(self.primary_evidence_ids),
            "reason": self.reason,
            "category_assessment": (
                {
                    "selected_room_category": (
                        assessment.selected_room_category.value
                        if assessment.selected_room_category is not None
                        else None
                    ),
                    "eligible_room_category": (
                        assessment.eligible_room_category.value
                        if assessment.eligible_room_category is not None
                        else None
                    ),
                    "status": assessment.status.value,
                    "reason": assessment.reason,
                }
                if assessment is not None
                else None
            ),
            "financial_calculation": "not_supported",
        }


def evaluate_authoritative_room_rent_eligibility(
    *,
    artifact_path: str | Path,
    scenario_id: str,
    entity_id: str,
    selected_room_category: str | None,
    icu_stay: bool | None,
) -> RoomRentEligibilityDecision:
    """Evaluate published room-rent category rules against explicit inputs.

    ``icu_stay`` is required because an ICU exception may supersede the ordinary
    room-category hierarchy. Unknown / contradictory inputs fail closed with an
    indeterminate result.
    """
    if not scenario_id.strip():
        raise ValueError("scenario_id must not be blank.")
    if not entity_id.strip():
        raise ValueError("entity_id must not be blank.")

    resolution = ConditionalRuleResolver().resolve(
        artifact_path,
        ConditionalRuleQuery(entity_id=entity_id, concept_id="room_rent"),
    )
    rules = tuple(resolution.rules)
    room_rule = _single_rule(rules, "room_category_constraint")
    icu_rule = _single_rule(rules, "icu_room_rent_exception")

    if icu_stay is None:
        return _indeterminate(
            scenario_id=scenario_id,
            entity_id=entity_id,
            rules=(room_rule, icu_rule),
            reason="ICU stay status is required because the published policy contains a separate ICU exception.",
        )
    if not isinstance(icu_stay, bool):
        return _indeterminate(
            scenario_id=scenario_id,
            entity_id=entity_id,
            rules=(room_rule, icu_rule),
            reason="ICU stay must be supplied as a boolean value.",
        )

    if icu_stay:
        if icu_rule is None:
            return _indeterminate(
                scenario_id=scenario_id,
                entity_id=entity_id,
                rules=(room_rule,),
                reason="No unique published ICU exception rule is available for this product.",
            )
        return RoomRentEligibilityDecision(
            scenario_id=scenario_id,
            entity_id=entity_id,
            status=RoomRentEligibilityStatus.ICU_EXCEPTION_APPLIES,
            rule_ids=(str(icu_rule["rule_id"]),),
            primary_evidence_ids=_primary_evidence_ids((icu_rule,)),
            reason="The published ICU exception applies; ordinary room-category entitlement is not evaluated for this ICU scenario.",
        )

    if room_rule is None:
        return _indeterminate(
            scenario_id=scenario_id,
            entity_id=entity_id,
            rules=(icu_rule,),
            reason="No unique published room-category entitlement rule is available for this product.",
        )
    if not isinstance(selected_room_category, str) or not selected_room_category.strip():
        return _indeterminate(
            scenario_id=scenario_id,
            entity_id=entity_id,
            rules=(room_rule, icu_rule),
            reason="A non-empty selected room category is required for non-ICU room eligibility evaluation.",
        )

    effect = room_rule.get("effect")
    if not isinstance(effect, Mapping):
        return _indeterminate(
            scenario_id=scenario_id,
            entity_id=entity_id,
            rules=(room_rule, icu_rule),
            reason="The published room-category rule has no valid effect payload.",
        )
    if effect.get("operator") != "selected_room_category_must_not_exceed":
        return _indeterminate(
            scenario_id=scenario_id,
            entity_id=entity_id,
            rules=(room_rule, icu_rule),
            reason="The published room-category rule uses an unsupported eligibility operator.",
        )
    eligible_category = effect.get("value")
    if not isinstance(eligible_category, str):
        return _indeterminate(
            scenario_id=scenario_id,
            entity_id=entity_id,
            rules=(room_rule, icu_rule),
            reason="The published room-category rule has no usable entitlement category.",
        )

    selected_canonical = normalize_room_category(selected_room_category)
    if selected_canonical is RoomCategory.INTENSIVE_CARE_UNIT:
        return _indeterminate(
            scenario_id=scenario_id,
            entity_id=entity_id,
            rules=(room_rule, icu_rule),
            reason="Selected room is ICU while ICU stay is false; the scenario inputs are inconsistent.",
        )

    assessment = assess_room_category_eligibility(
        selected_room_category=selected_room_category,
        eligible_room_category=eligible_category,
        icu_stay=False,
    )
    if assessment.status is RoomEligibilityStatus.WITHIN_ENTITLEMENT:
        status = RoomRentEligibilityStatus.WITHIN_ENTITLEMENT
    elif assessment.status is RoomEligibilityStatus.POTENTIALLY_ABOVE_ENTITLEMENT:
        status = RoomRentEligibilityStatus.POTENTIALLY_ABOVE_ENTITLEMENT
    else:
        status = RoomRentEligibilityStatus.INDETERMINATE

    return RoomRentEligibilityDecision(
        scenario_id=scenario_id,
        entity_id=entity_id,
        status=status,
        rule_ids=(str(room_rule["rule_id"]),),
        primary_evidence_ids=_primary_evidence_ids((room_rule,)),
        reason=assessment.reason,
        category_assessment=assessment,
    )


def _single_rule(
    rules: tuple[Mapping[str, Any], ...],
    rule_type: str,
) -> Mapping[str, Any] | None:
    matches = tuple(rule for rule in rules if rule.get("rule_type") == rule_type)
    return matches[0] if len(matches) == 1 else None


def _primary_evidence_ids(rules: tuple[Mapping[str, Any] | None, ...]) -> tuple[str, ...]:
    values: list[str] = []
    for rule in rules:
        if rule is None:
            continue
        evidence = rule.get("evidence")
        if not isinstance(evidence, Mapping):
            continue
        primary = evidence.get("primary_evidence")
        if not isinstance(primary, Mapping):
            continue
        evidence_id = primary.get("evidence_id")
        if isinstance(evidence_id, str) and evidence_id:
            values.append(evidence_id)
    return tuple(values)


def _indeterminate(
    *,
    scenario_id: str,
    entity_id: str,
    rules: tuple[Mapping[str, Any] | None, ...],
    reason: str,
) -> RoomRentEligibilityDecision:
    resolved_rules = tuple(rule for rule in rules if rule is not None)
    return RoomRentEligibilityDecision(
        scenario_id=scenario_id,
        entity_id=entity_id,
        status=RoomRentEligibilityStatus.INDETERMINATE,
        rule_ids=tuple(str(rule["rule_id"]) for rule in resolved_rules),
        primary_evidence_ids=_primary_evidence_ids(resolved_rules),
        reason=reason,
    )
