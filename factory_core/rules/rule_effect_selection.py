"""Explicit selection contract for allowed-set conditional-rule effects.

A published allowed-set effect is policy evidence, not a selected customer value.
This module validates an explicit selection supplied by a user or extracted from a
quote, then creates an ephemeral fixed-effect rule for downstream evaluation.
It never writes back to the authoritative rule artifact, defaults a value, or
recommends one option over another.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from factory_core.rules.conditional_rule_models import (
    ConditionalRule,
    RuleAssemblyStatus,
    RuleEffect,
    RuleEffectValueKind,
)


class RuleEffectSelectionStatus(StrEnum):
    SELECTED = "selected"
    REJECTED = "rejected"


class RuleEffectSelectionSource(StrEnum):
    USER_PROVIDED = "user_provided"
    QUOTE_EXTRACTED = "quote_extracted"


@dataclass(frozen=True, slots=True)
class RuleEffectSelection:
    """An explicit, validated selection against one allowed-set rule.

    ``source_reference_id`` is an opaque input/evidence reference. It is not
    raw user text and lets a later trace identify where the selection came from.
    """

    rule_id: str
    status: RuleEffectSelectionStatus
    source: RuleEffectSelectionSource
    source_reference_id: str
    selected_value: Decimal | None
    allowed_values: tuple[Decimal, ...]
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("RuleEffectSelection.rule_id must not be blank.")
        if not self.source_reference_id.strip():
            raise ValueError("RuleEffectSelection.source_reference_id must not be blank.")
        if len(set(self.allowed_values)) != len(self.allowed_values):
            raise ValueError("RuleEffectSelection.allowed_values must be unique.")
        if self.status is RuleEffectSelectionStatus.SELECTED:
            if not self.allowed_values:
                raise ValueError("Selected RuleEffectSelection requires allowed_values.")
            if self.selected_value is None:
                raise ValueError("Selected RuleEffectSelection requires selected_value.")
            if self.selected_value not in self.allowed_values:
                raise ValueError("Selected value must be one of allowed_values.")
            if self.reasons:
                raise ValueError("Selected RuleEffectSelection cannot carry rejection reasons.")
        else:
            if self.selected_value is not None:
                raise ValueError("Rejected RuleEffectSelection must not expose selected_value.")
            if not self.reasons:
                raise ValueError("Rejected RuleEffectSelection requires one or more reasons.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "status": self.status.value,
            "source": self.source.value,
            "source_reference_id": self.source_reference_id,
            "selected_value": None if self.selected_value is None else format(self.selected_value, "f"),
            "allowed_values": [format(value, "f") for value in self.allowed_values],
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True, slots=True)
class SelectedRuleForEvaluation:
    """Ephemeral fixed-effect projection of a published allowed-set rule.

    The embedded rule is for one evaluation only. The source authoritative rule
    remains an allowed-set rule and is never mutated or republished.
    """

    source_rule_id: str
    selection: RuleEffectSelection
    evaluation_rule: ConditionalRule

    def __post_init__(self) -> None:
        if self.source_rule_id != self.selection.rule_id:
            raise ValueError("Selection must belong to source_rule_id.")
        if self.evaluation_rule.rule_id != self.source_rule_id:
            raise ValueError("Evaluation rule must retain the source rule_id.")
        if self.selection.status is not RuleEffectSelectionStatus.SELECTED:
            raise ValueError("Only selected effects may create an evaluation rule.")
        if self.evaluation_rule.effect.value_kind is not RuleEffectValueKind.FIXED:
            raise ValueError("Evaluation rule must use a fixed effect value.")
        if self.evaluation_rule.effect.value != self.selection.selected_value:
            raise ValueError("Evaluation rule effect must match selected value.")


class RuleEffectSelectionValidator:
    """Validate explicit values for evidence-backed allowed-set rule effects."""

    validator_id = "factory_core.rule_effect_selection_validator"
    validator_version = "1.0"

    def validate(
        self,
        rule: ConditionalRule,
        selected_value: Decimal | int | float | str | None,
        *,
        source: RuleEffectSelectionSource,
        source_reference_id: str,
    ) -> RuleEffectSelection:
        if rule.status is not RuleAssemblyStatus.EVIDENCE_ASSEMBLED_NOT_FACT_EXTRACTED:
            raise ValueError("Selections accept only evidence-assembled rules.")
        if rule.unresolved_ambiguities:
            raise ValueError("Selections reject rules with unresolved ambiguities.")
        allowed_values = _allowed_decimals(rule)
        if rule.effect.value_kind is not RuleEffectValueKind.ALLOWED_SET:
            return self._rejected(
                rule, source, source_reference_id, allowed_values,
                "This rule does not expose a selectable allowed-set effect.",
            )
        value = _decimal(selected_value)
        if value is None:
            return self._rejected(
                rule, source, source_reference_id, allowed_values,
                "A selected value must be an explicit finite number.",
            )
        if value not in allowed_values:
            return self._rejected(
                rule, source, source_reference_id, allowed_values,
                "Selected value is not one of the evidence-backed allowed values.",
            )
        return RuleEffectSelection(
            rule_id=rule.rule_id,
            status=RuleEffectSelectionStatus.SELECTED,
            source=source,
            source_reference_id=source_reference_id,
            selected_value=value,
            allowed_values=allowed_values,
        )

    @staticmethod
    def _rejected(
        rule: ConditionalRule,
        source: RuleEffectSelectionSource,
        source_reference_id: str,
        allowed_values: tuple[Decimal, ...],
        reason: str,
    ) -> RuleEffectSelection:
        return RuleEffectSelection(
            rule_id=rule.rule_id,
            status=RuleEffectSelectionStatus.REJECTED,
            source=source,
            source_reference_id=source_reference_id,
            selected_value=None,
            allowed_values=allowed_values,
            reasons=(reason,),
        )


def select_rule_effect_value(
    rule: ConditionalRule,
    selected_value: Decimal | int | float | str | None,
    *,
    source: RuleEffectSelectionSource,
    source_reference_id: str,
) -> RuleEffectSelection:
    return RuleEffectSelectionValidator().validate(
        rule,
        selected_value,
        source=source,
        source_reference_id=source_reference_id,
    )


def build_selected_rule_for_evaluation(
    rule: ConditionalRule,
    selection: RuleEffectSelection,
) -> SelectedRuleForEvaluation:
    """Create an in-memory fixed-effect projection after successful validation."""
    if selection.rule_id != rule.rule_id:
        raise ValueError("Selection must belong to the supplied rule.")
    if selection.status is not RuleEffectSelectionStatus.SELECTED:
        raise ValueError("Rejected selections cannot create an evaluation rule.")
    assert selection.selected_value is not None
    evaluation_rule = replace(
        rule,
        effect=RuleEffect(
            operator=rule.effect.operator,
            value=selection.selected_value,
            unit=rule.effect.unit,
            basis=rule.effect.basis,
            value_kind=RuleEffectValueKind.FIXED,
        ),
    )
    return SelectedRuleForEvaluation(
        source_rule_id=rule.rule_id,
        selection=selection,
        evaluation_rule=evaluation_rule,
    )


def _allowed_decimals(rule: ConditionalRule) -> tuple[Decimal, ...]:
    raw = rule.effect.value
    if not isinstance(raw, tuple):
        return ()
    values = tuple(value for value in (_decimal(item) for item in raw) if value is not None)
    return tuple(sorted(set(values)))


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None
