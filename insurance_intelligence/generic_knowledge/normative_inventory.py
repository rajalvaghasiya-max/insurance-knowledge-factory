"""Generic normative-inventory and residue accounting for MO-028B.G3.

The inventory path is intentionally separate from semantic mapping.  This module does not
recognize product facts from prose and does not branch on insurer/product identity.  It accepts
source-anchored ``NormativeUnit`` values produced by an independent high-recall inventory path,
then accounts every unit against governed semantic/relationship outputs.  Any material unit that
is not explicitly and validly accounted for remains visible as residue and blocks only its own
applicability unit.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

from insurance_intelligence.generic_knowledge.contracts import (
    AccountingState,
    ApplicabilityKey,
    GenericKnowledgeContractError,
    NormativeUnit,
    PublicationBlocker,
    RelationshipFact,
    ResidueRecord,
    SemanticFact,
    blocker_for_residue,
)


class NormativeInventoryError(GenericKnowledgeContractError):
    """Raised when inventory/accounting inputs violate G0/G1 governance."""


class InventoryReviewStatus(str, Enum):
    UNREVIEWED = "UNREVIEWED"
    REVIEWED = "REVIEWED"


@dataclass(frozen=True)
class NormativeInventory:
    concept: str
    inventory_method: str
    inventory_version: str
    review_status: InventoryReviewStatus
    units: tuple[NormativeUnit, ...]

    def __post_init__(self) -> None:
        for field_name in ("concept", "inventory_method", "inventory_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise NormativeInventoryError(f"{field_name} must be non-empty text")
            object.__setattr__(self, field_name, value.strip())
        if not isinstance(self.review_status, InventoryReviewStatus):
            raise NormativeInventoryError("review_status must be an InventoryReviewStatus")
        if not self.units:
            raise NormativeInventoryError("inventory must contain at least one NormativeUnit")
        seen: set[str] = set()
        for unit in self.units:
            if not isinstance(unit, NormativeUnit):
                raise NormativeInventoryError("all inventory units must be NormativeUnit values")
            if unit.concept != self.concept:
                raise NormativeInventoryError(
                    "inventory unit concept must match inventory concept"
                )
            if unit.normative_unit_id in seen:
                raise NormativeInventoryError(
                    f"duplicate normative_unit_id: {unit.normative_unit_id}"
                )
            seen.add(unit.normative_unit_id)


@dataclass(frozen=True)
class InventoryAccountingDecision:
    normative_unit_id: str
    accounting_state: AccountingState
    reason: str
    semantic_fact_ids: tuple[str, ...] = ()
    relationship_fact_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.normative_unit_id, str) or not self.normative_unit_id.strip():
            raise NormativeInventoryError("normative_unit_id must be non-empty text")
        object.__setattr__(self, "normative_unit_id", self.normative_unit_id.strip())
        if not isinstance(self.accounting_state, AccountingState):
            raise NormativeInventoryError("accounting_state must be an AccountingState")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise NormativeInventoryError("reason must be non-empty text")
        object.__setattr__(self, "reason", self.reason.strip())
        semantic_ids = tuple(_required_id(value, "semantic_fact_ids") for value in self.semantic_fact_ids)
        relationship_ids = tuple(
            _required_id(value, "relationship_fact_ids") for value in self.relationship_fact_ids
        )
        object.__setattr__(self, "semantic_fact_ids", semantic_ids)
        object.__setattr__(self, "relationship_fact_ids", relationship_ids)

        if self.accounting_state is AccountingState.MAPPED and not semantic_ids:
            raise NormativeInventoryError("MAPPED decision requires semantic_fact_ids")
        if self.accounting_state is AccountingState.MAPPED_AS_RELATIONSHIP and not relationship_ids:
            raise NormativeInventoryError(
                "MAPPED_AS_RELATIONSHIP decision requires relationship_fact_ids"
            )
        if self.accounting_state is not AccountingState.MAPPED and semantic_ids:
            raise NormativeInventoryError(
                "semantic_fact_ids are allowed only for MAPPED decisions"
            )
        if self.accounting_state is not AccountingState.MAPPED_AS_RELATIONSHIP and relationship_ids:
            raise NormativeInventoryError(
                "relationship_fact_ids are allowed only for MAPPED_AS_RELATIONSHIP decisions"
            )


@dataclass(frozen=True)
class ResidueTelemetry:
    concept: str
    normative_unit_count: int
    accounted_unit_count: int
    residue_count: int
    blocking_residue_count: int
    state_counts: Mapping[AccountingState, int]


@dataclass(frozen=True)
class InventoryAccountingResult:
    concept: str
    inventory_method: str
    inventory_version: str
    residues: tuple[ResidueRecord, ...]
    blockers: tuple[PublicationBlocker, ...]
    telemetry: ResidueTelemetry

    @property
    def publishable(self) -> bool:
        return not self.blockers


def _required_id(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NormativeInventoryError(f"{field_name} must contain non-empty identifiers")
    return value.strip()


def _same_applicability(left: ApplicabilityKey, right: ApplicabilityKey) -> bool:
    return left == right


def _index_semantic_facts(facts: Sequence[SemanticFact]) -> dict[str, SemanticFact]:
    indexed: dict[str, SemanticFact] = {}
    for fact in facts:
        if not isinstance(fact, SemanticFact):
            raise NormativeInventoryError("semantic_facts must contain SemanticFact values")
        if fact.fact_id in indexed:
            raise NormativeInventoryError(f"duplicate semantic fact id: {fact.fact_id}")
        indexed[fact.fact_id] = fact
    return indexed


def _index_relationship_facts(
    facts: Sequence[RelationshipFact],
) -> dict[str, RelationshipFact]:
    indexed: dict[str, RelationshipFact] = {}
    for fact in facts:
        if not isinstance(fact, RelationshipFact):
            raise NormativeInventoryError(
                "relationship_facts must contain RelationshipFact values"
            )
        if fact.relationship_id in indexed:
            raise NormativeInventoryError(
                f"duplicate relationship fact id: {fact.relationship_id}"
            )
        indexed[fact.relationship_id] = fact
    return indexed


def _validate_decision_mapping(
    unit: NormativeUnit,
    decision: InventoryAccountingDecision,
    semantic_facts: Mapping[str, SemanticFact],
    relationship_facts: Mapping[str, RelationshipFact],
) -> None:
    if decision.accounting_state is AccountingState.MAPPED:
        for fact_id in decision.semantic_fact_ids:
            fact = semantic_facts.get(fact_id)
            if fact is None:
                raise NormativeInventoryError(
                    f"accounting references unknown semantic fact: {fact_id}"
                )
            if fact.concept != unit.concept:
                raise NormativeInventoryError(
                    "mapped semantic fact concept must match normative unit concept"
                )
            if not _same_applicability(fact.applicability, unit.applicability):
                raise NormativeInventoryError(
                    "mapped semantic fact applicability must match normative unit applicability"
                )
            if unit.evidence.evidence_id not in fact.evidence_ids:
                raise NormativeInventoryError(
                    "mapped semantic fact must retain the normative unit evidence id"
                )

    if decision.accounting_state is AccountingState.MAPPED_AS_RELATIONSHIP:
        for relationship_id in decision.relationship_fact_ids:
            fact = relationship_facts.get(relationship_id)
            if fact is None:
                raise NormativeInventoryError(
                    f"accounting references unknown relationship fact: {relationship_id}"
                )
            if unit.concept not in (fact.source_concept, fact.target_concept):
                raise NormativeInventoryError(
                    "mapped relationship must attach to the normative unit concept"
                )
            if not _same_applicability(fact.applicability, unit.applicability):
                raise NormativeInventoryError(
                    "mapped relationship applicability must match normative unit applicability"
                )
            if unit.evidence.evidence_id not in fact.evidence_ids:
                raise NormativeInventoryError(
                    "mapped relationship must retain the normative unit evidence id"
                )


def _residue_for(
    unit: NormativeUnit,
    state: AccountingState,
    reason: str,
) -> ResidueRecord:
    return ResidueRecord(
        residue_id=f"residue_{unit.normative_unit_id}",
        normative_unit_id=unit.normative_unit_id,
        concept=unit.concept,
        applicability=unit.applicability,
        accounting_state=state,
        reason=reason,
        # NormativeUnit already requires one or more source-defined material consequences.
        # Therefore an unresolved inventory unit is material by construction.
        material=True,
    )


def account_normative_inventory(
    inventory: NormativeInventory,
    *,
    decisions: Sequence[InventoryAccountingDecision],
    semantic_facts: Sequence[SemanticFact] = (),
    relationship_facts: Sequence[RelationshipFact] = (),
) -> InventoryAccountingResult:
    """Account every inventory unit and expose unresolved material residue.

    Missing accounting decisions do not disappear: they become material
    ``DEFERRED_WITH_REASON`` residue. Mapping decisions must retain concept, applicability and
    source evidence. This keeps the gate independent of whether a mapper produced a syntactically
    valid record.
    """
    if not isinstance(inventory, NormativeInventory):
        raise NormativeInventoryError("inventory must be a NormativeInventory")

    semantic_index = _index_semantic_facts(semantic_facts)
    relationship_index = _index_relationship_facts(relationship_facts)

    unit_ids = {unit.normative_unit_id for unit in inventory.units}
    decision_index: dict[str, InventoryAccountingDecision] = {}
    for decision in decisions:
        if not isinstance(decision, InventoryAccountingDecision):
            raise NormativeInventoryError(
                "decisions must contain InventoryAccountingDecision values"
            )
        if decision.normative_unit_id not in unit_ids:
            raise NormativeInventoryError(
                f"accounting decision references unknown normative unit: {decision.normative_unit_id}"
            )
        if decision.normative_unit_id in decision_index:
            raise NormativeInventoryError(
                f"duplicate accounting decision for normative unit: {decision.normative_unit_id}"
            )
        decision_index[decision.normative_unit_id] = decision

    residues: list[ResidueRecord] = []
    state_counts: dict[AccountingState, int] = {state: 0 for state in AccountingState}

    for unit in inventory.units:
        decision = decision_index.get(unit.normative_unit_id)
        if decision is None:
            state = AccountingState.DEFERRED_WITH_REASON
            state_counts[state] += 1
            residues.append(
                _residue_for(
                    unit,
                    state,
                    "no explicit accounting decision exists for this normative unit",
                )
            )
            continue

        state_counts[decision.accounting_state] += 1
        _validate_decision_mapping(
            unit,
            decision,
            semantic_index,
            relationship_index,
        )

        if decision.accounting_state in (
            AccountingState.MAPPED,
            AccountingState.MAPPED_AS_RELATIONSHIP,
            AccountingState.EXPLICITLY_NON_APPLICABLE,
            AccountingState.DUPLICATE_CORROBORATING,
        ):
            continue

        residues.append(
            _residue_for(unit, decision.accounting_state, decision.reason)
        )

    blockers = tuple(
        blocker
        for residue in residues
        if (blocker := blocker_for_residue(residue)) is not None
    )
    telemetry = ResidueTelemetry(
        concept=inventory.concept,
        normative_unit_count=len(inventory.units),
        accounted_unit_count=len(decision_index),
        residue_count=len(residues),
        blocking_residue_count=len(blockers),
        state_counts=state_counts,
    )
    return InventoryAccountingResult(
        concept=inventory.concept,
        inventory_method=inventory.inventory_method,
        inventory_version=inventory.inventory_version,
        residues=tuple(residues),
        blockers=blockers,
        telemetry=telemetry,
    )


__all__ = [
    "InventoryAccountingDecision",
    "InventoryAccountingResult",
    "InventoryReviewStatus",
    "NormativeInventory",
    "NormativeInventoryError",
    "ResidueTelemetry",
    "account_normative_inventory",
]
