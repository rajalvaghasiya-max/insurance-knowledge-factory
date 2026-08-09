"""Generic reviewed waiting-period semantic and relationship mapping for MO-028B.G6.

This module does not infer product facts directly from prose.  It consumes source-anchored
NormativeUnit values plus explicit reviewed mapping instructions, validates those instructions
against reusable waiting-period ontology semantics, preserves applicability/evidence, and emits
Generic Knowledge SemanticFact / RelationshipFact records plus G3 accounting decisions.
Unsupported semantics fail closed as NOT_YET_REPRESENTABLE residue.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from insurance_intelligence.benefits.waiting_period_contracts import (
    WaitingPeriodDurationUnit,
    WaitingPeriodStartBasis,
    WaitingPeriodType,
)
from insurance_intelligence.generic_knowledge.contracts import (
    AccountingState,
    GenericKnowledgeContractError,
    NormativeUnit,
    RelationshipFact,
    RelationshipType,
    SemanticFact,
)
from insurance_intelligence.generic_knowledge.normative_inventory import (
    InventoryAccountingDecision,
)


WAITING_PERIOD_CONCEPT = "waiting_periods"


class WaitingPeriodMappingError(GenericKnowledgeContractError):
    """Raised when reviewed waiting-period mapping input is structurally invalid."""


class WaitingPeriodSemanticType(str, Enum):
    BASE_MECHANIC = "BASE_MECHANIC"
    DURATION = "DURATION"
    START_BASIS = "START_BASIS"
    SCOPE = "SCOPE"
    EXCEPTION = "EXCEPTION"
    CONTINUITY = "CONTINUITY"
    PORTABILITY = "PORTABILITY"
    SUM_INSURED_ENHANCEMENT = "SUM_INSURED_ENHANCEMENT"
    SCHEDULE_DEPENDENCY = "SCHEDULE_DEPENDENCY"
    RENEWAL_EFFECT = "RENEWAL_EFFECT"


class ReviewedMappingKind(str, Enum):
    SEMANTIC_FACT = "SEMANTIC_FACT"
    RELATIONSHIP_FACT = "RELATIONSHIP_FACT"
    EXPLICITLY_NON_APPLICABLE = "EXPLICITLY_NON_APPLICABLE"
    DUPLICATE_CORROBORATING = "DUPLICATE_CORROBORATING"
    NOT_YET_REPRESENTABLE = "NOT_YET_REPRESENTABLE"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodMappingError(f"{field_name} must be non-empty text")
    return value.strip()


@dataclass(frozen=True)
class ReviewedWaitingPeriodMapping:
    """Human/governed mapping decision for one normative unit."""

    normative_unit_id: str
    kind: ReviewedMappingKind
    reason: str
    semantic_type: WaitingPeriodSemanticType | None = None
    semantic_value: Mapping[str, Any] | None = None
    relationship_type: RelationshipType | None = None
    source_concept: str | None = None
    target_concept: str | None = None
    relationship_condition: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "normative_unit_id", _text(self.normative_unit_id, "normative_unit_id"))
        object.__setattr__(self, "reason", _text(self.reason, "reason"))
        if not isinstance(self.kind, ReviewedMappingKind):
            raise WaitingPeriodMappingError("kind must be a ReviewedMappingKind")

        if self.kind is ReviewedMappingKind.SEMANTIC_FACT:
            if not isinstance(self.semantic_type, WaitingPeriodSemanticType):
                raise WaitingPeriodMappingError("SEMANTIC_FACT requires semantic_type")
            if not isinstance(self.semantic_value, Mapping) or not self.semantic_value:
                raise WaitingPeriodMappingError("SEMANTIC_FACT requires non-empty semantic_value")
            if any(
                value is not None
                for value in (
                    self.relationship_type,
                    self.source_concept,
                    self.target_concept,
                    self.relationship_condition,
                )
            ):
                raise WaitingPeriodMappingError("semantic mapping cannot also define relationship fields")
        elif self.kind is ReviewedMappingKind.RELATIONSHIP_FACT:
            if not isinstance(self.relationship_type, RelationshipType):
                raise WaitingPeriodMappingError("RELATIONSHIP_FACT requires relationship_type")
            if self.source_concept is None or self.target_concept is None:
                raise WaitingPeriodMappingError("RELATIONSHIP_FACT requires source_concept and target_concept")
            object.__setattr__(self, "source_concept", _text(self.source_concept, "source_concept"))
            object.__setattr__(self, "target_concept", _text(self.target_concept, "target_concept"))
            if not isinstance(self.relationship_condition, Mapping):
                raise WaitingPeriodMappingError("RELATIONSHIP_FACT requires relationship_condition mapping")
            if self.semantic_type is not None or self.semantic_value is not None:
                raise WaitingPeriodMappingError("relationship mapping cannot also define semantic fields")
        else:
            if any(
                value is not None
                for value in (
                    self.semantic_type,
                    self.semantic_value,
                    self.relationship_type,
                    self.source_concept,
                    self.target_concept,
                    self.relationship_condition,
                )
            ):
                raise WaitingPeriodMappingError(
                    f"{self.kind.value} mapping cannot define fact fields"
                )


@dataclass(frozen=True)
class WaitingPeriodMappingResult:
    semantic_facts: tuple[SemanticFact, ...]
    relationship_facts: tuple[RelationshipFact, ...]
    accounting_decisions: tuple[InventoryAccountingDecision, ...]


def _waiting_period_type(value: object) -> str:
    try:
        return WaitingPeriodType(str(value)).value
    except ValueError as exc:
        raise WaitingPeriodMappingError("waiting_period_type is not supported by the ontology") from exc


def _validate_semantic_value(
    semantic_type: WaitingPeriodSemanticType,
    value: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = dict(value)
    if "waiting_period_type" not in normalized:
        raise WaitingPeriodMappingError("semantic_value requires waiting_period_type")
    normalized["waiting_period_type"] = _waiting_period_type(normalized["waiting_period_type"])

    if semantic_type in (WaitingPeriodSemanticType.BASE_MECHANIC, WaitingPeriodSemanticType.DURATION):
        duration_value = normalized.get("duration_value")
        duration_unit = normalized.get("duration_unit")
        if type(duration_value) is not int or duration_value < 0:
            raise WaitingPeriodMappingError("duration_value must be a non-negative integer")
        try:
            normalized["duration_unit"] = WaitingPeriodDurationUnit(str(duration_unit)).value
        except ValueError as exc:
            raise WaitingPeriodMappingError("duration_unit is not supported by the ontology") from exc

    if semantic_type is WaitingPeriodSemanticType.BASE_MECHANIC:
        try:
            normalized["start_basis"] = WaitingPeriodStartBasis(str(normalized.get("start_basis"))).value
        except ValueError as exc:
            raise WaitingPeriodMappingError("start_basis is not supported by the ontology") from exc
        applies_to = normalized.get("applies_to")
        if not isinstance(applies_to, (list, tuple)) or not applies_to:
            raise WaitingPeriodMappingError("BASE_MECHANIC requires non-empty applies_to")
        normalized["applies_to"] = tuple(_text(item, "applies_to") for item in applies_to)

    if semantic_type is WaitingPeriodSemanticType.START_BASIS:
        try:
            normalized["start_basis"] = WaitingPeriodStartBasis(str(normalized.get("start_basis"))).value
        except ValueError as exc:
            raise WaitingPeriodMappingError("start_basis is not supported by the ontology") from exc

    if semantic_type in (
        WaitingPeriodSemanticType.SCOPE,
        WaitingPeriodSemanticType.EXCEPTION,
        WaitingPeriodSemanticType.CONTINUITY,
        WaitingPeriodSemanticType.PORTABILITY,
        WaitingPeriodSemanticType.SUM_INSURED_ENHANCEMENT,
        WaitingPeriodSemanticType.SCHEDULE_DEPENDENCY,
        WaitingPeriodSemanticType.RENEWAL_EFFECT,
    ):
        detail = normalized.get("detail")
        normalized["detail"] = _text(detail, "detail")

    return normalized


def _fact_id(unit: NormativeUnit, semantic_type: WaitingPeriodSemanticType) -> str:
    return f"fact_{unit.normative_unit_id}_{semantic_type.value.lower()}"


def _relationship_id(unit: NormativeUnit, relationship_type: RelationshipType) -> str:
    return f"rel_{unit.normative_unit_id}_{relationship_type.value.lower()}"


def map_reviewed_waiting_period_units(
    units: Sequence[NormativeUnit],
    mappings: Sequence[ReviewedWaitingPeriodMapping],
    *,
    ontology_version: str,
) -> WaitingPeriodMappingResult:
    """Map reviewed normative units into generic facts and explicit accounting decisions."""
    ontology_version = _text(ontology_version, "ontology_version")
    unit_index: dict[str, NormativeUnit] = {}
    for unit in units:
        if not isinstance(unit, NormativeUnit):
            raise WaitingPeriodMappingError("units must contain NormativeUnit values")
        if unit.concept != WAITING_PERIOD_CONCEPT:
            raise WaitingPeriodMappingError("all units must belong to waiting_periods concept")
        if unit.normative_unit_id in unit_index:
            raise WaitingPeriodMappingError(f"duplicate normative unit: {unit.normative_unit_id}")
        unit_index[unit.normative_unit_id] = unit

    mapping_index: dict[str, ReviewedWaitingPeriodMapping] = {}
    for mapping in mappings:
        if not isinstance(mapping, ReviewedWaitingPeriodMapping):
            raise WaitingPeriodMappingError("mappings must contain ReviewedWaitingPeriodMapping values")
        if mapping.normative_unit_id not in unit_index:
            raise WaitingPeriodMappingError(
                f"mapping references unknown normative unit: {mapping.normative_unit_id}"
            )
        if mapping.normative_unit_id in mapping_index:
            raise WaitingPeriodMappingError(
                f"duplicate reviewed mapping for normative unit: {mapping.normative_unit_id}"
            )
        mapping_index[mapping.normative_unit_id] = mapping

    semantic_facts: list[SemanticFact] = []
    relationship_facts: list[RelationshipFact] = []
    decisions: list[InventoryAccountingDecision] = []

    for unit in units:
        mapping = mapping_index.get(unit.normative_unit_id)
        if mapping is None:
            decisions.append(
                InventoryAccountingDecision(
                    normative_unit_id=unit.normative_unit_id,
                    accounting_state=AccountingState.DEFERRED_WITH_REASON,
                    reason="no reviewed waiting-period mapping instruction exists",
                )
            )
            continue

        if mapping.kind is ReviewedMappingKind.SEMANTIC_FACT:
            assert mapping.semantic_type is not None
            assert mapping.semantic_value is not None
            value = _validate_semantic_value(mapping.semantic_type, mapping.semantic_value)
            fact = SemanticFact(
                fact_id=_fact_id(unit, mapping.semantic_type),
                concept=WAITING_PERIOD_CONCEPT,
                semantic_type=mapping.semantic_type.value,
                value=value,
                applicability=unit.applicability,
                evidence_ids=(unit.evidence.evidence_id,),
                ontology_version=ontology_version,
            )
            semantic_facts.append(fact)
            decisions.append(
                InventoryAccountingDecision(
                    normative_unit_id=unit.normative_unit_id,
                    accounting_state=AccountingState.MAPPED,
                    reason=mapping.reason,
                    semantic_fact_ids=(fact.fact_id,),
                )
            )
            continue

        if mapping.kind is ReviewedMappingKind.RELATIONSHIP_FACT:
            assert mapping.relationship_type is not None
            assert mapping.source_concept is not None
            assert mapping.target_concept is not None
            assert mapping.relationship_condition is not None
            if WAITING_PERIOD_CONCEPT not in (mapping.source_concept, mapping.target_concept):
                raise WaitingPeriodMappingError(
                    "waiting-period relationship must attach to waiting_periods concept"
                )
            relationship = RelationshipFact(
                relationship_id=_relationship_id(unit, mapping.relationship_type),
                source_concept=mapping.source_concept,
                relationship_type=mapping.relationship_type,
                target_concept=mapping.target_concept,
                condition=dict(mapping.relationship_condition),
                applicability=unit.applicability,
                evidence_ids=(unit.evidence.evidence_id,),
                ontology_version=ontology_version,
            )
            relationship_facts.append(relationship)
            decisions.append(
                InventoryAccountingDecision(
                    normative_unit_id=unit.normative_unit_id,
                    accounting_state=AccountingState.MAPPED_AS_RELATIONSHIP,
                    reason=mapping.reason,
                    relationship_fact_ids=(relationship.relationship_id,),
                )
            )
            continue

        state = {
            ReviewedMappingKind.EXPLICITLY_NON_APPLICABLE: AccountingState.EXPLICITLY_NON_APPLICABLE,
            ReviewedMappingKind.DUPLICATE_CORROBORATING: AccountingState.DUPLICATE_CORROBORATING,
            ReviewedMappingKind.NOT_YET_REPRESENTABLE: AccountingState.NOT_YET_REPRESENTABLE,
        }[mapping.kind]
        decisions.append(
            InventoryAccountingDecision(
                normative_unit_id=unit.normative_unit_id,
                accounting_state=state,
                reason=mapping.reason,
            )
        )

    return WaitingPeriodMappingResult(
        semantic_facts=tuple(semantic_facts),
        relationship_facts=tuple(relationship_facts),
        accounting_decisions=tuple(decisions),
    )


__all__ = [
    "ReviewedMappingKind",
    "ReviewedWaitingPeriodMapping",
    "WAITING_PERIOD_CONCEPT",
    "WaitingPeriodMappingError",
    "WaitingPeriodMappingResult",
    "WaitingPeriodSemanticType",
    "map_reviewed_waiting_period_units",
]
