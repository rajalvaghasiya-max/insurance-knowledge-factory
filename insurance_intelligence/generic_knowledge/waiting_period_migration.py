"""Generic data-driven waiting-period migration loader for MO-028B.G8.

Product-specific values live in governed migration records. This module validates those records,
creates source-anchored NormativeUnit values and reviewed G6 mapping instructions, then runs the
generic mapper and residue accounting path. It must never branch on insurer/product identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from insurance_intelligence.generic_knowledge.contracts import (
    ApplicabilityKey,
    EvidenceReference,
    GenericKnowledgeContractError,
    NormativeUnit,
    NormativeUnitKind,
)
from insurance_intelligence.generic_knowledge.normative_inventory import (
    InventoryAccountingResult,
    InventoryReviewStatus,
    NormativeInventory,
    account_normative_inventory,
)
from insurance_intelligence.generic_knowledge.waiting_period_mapping import (
    ReviewedMappingKind,
    ReviewedWaitingPeriodMapping,
    WaitingPeriodMappingResult,
    WaitingPeriodSemanticType,
    map_reviewed_waiting_period_units,
)


class WaitingPeriodMigrationError(GenericKnowledgeContractError):
    """Raised when a governed migration record is invalid."""


@dataclass(frozen=True)
class WaitingPeriodMigrationResult:
    applicability: ApplicabilityKey
    source_document_id: str
    source_document_version: str
    source_hash_sha256: str
    ontology_version: str
    review_decision_version: str
    mapping: WaitingPeriodMappingResult
    accounting: InventoryAccountingResult


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodMigrationError(f"{name} must be non-empty text")
    return value.strip()


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise WaitingPeriodMigrationError(f"{name} must be a mapping")
    return value


def _sequence(value: object, name: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise WaitingPeriodMigrationError(f"{name} must be a list")
    return value


def migrate_waiting_period_record(record: Mapping[str, Any]) -> WaitingPeriodMigrationResult:
    """Run a governed waiting-period migration record through G6 + G3 generically."""
    record = _mapping(record, "record")
    if record.get("record_type") != "generic_waiting_period_migration_v1":
        raise WaitingPeriodMigrationError("unsupported migration record_type")

    applicability = ApplicabilityKey(
        product_reference=_text(record.get("product_reference"), "product_reference"),
        policy_version=_text(record.get("policy_version"), "policy_version"),
    )
    ontology_version = _text(record.get("ontology_version"), "ontology_version")
    review_decision_version = _text(
        record.get("review_decision_version"), "review_decision_version"
    )
    source = _mapping(record.get("source"), "source")
    document_id = _text(source.get("document_id"), "source.document_id")
    document_version = _text(source.get("document_version"), "source.document_version")
    source_hash = _text(source.get("sha256"), "source.sha256")
    authority_class = _text(source.get("authority_class"), "source.authority_class")

    units: list[NormativeUnit] = []
    mappings: list[ReviewedWaitingPeriodMapping] = []
    for raw in _sequence(record.get("units"), "units"):
        raw = _mapping(raw, "unit")
        unit_id = _text(raw.get("unit_id"), "unit_id")
        locator = _text(raw.get("locator"), "locator")
        evidence_id = _text(raw.get("evidence_id"), "evidence_id")
        materially_affects = tuple(
            _text(item, "materially_affects[]")
            for item in _sequence(raw.get("materially_affects"), "materially_affects")
        )
        evidence = EvidenceReference(
            evidence_id=evidence_id,
            source_document_id=document_id,
            source_document_version=document_version,
            source_hash_sha256=source_hash,
            locator=locator,
            authority_class=authority_class,
        )
        unit = NormativeUnit(
            normative_unit_id=unit_id,
            concept="waiting_periods",
            kind=NormativeUnitKind(_text(raw.get("kind"), "kind")),
            text_sha256=_text(raw.get("text_sha256"), "text_sha256"),
            excerpt=_text(raw.get("excerpt"), "excerpt"),
            applicability=applicability,
            evidence=evidence,
            materially_affects=materially_affects,
        )
        units.append(unit)

        reviewed = _mapping(raw.get("reviewed_mapping"), "reviewed_mapping")
        mapping_kind = ReviewedMappingKind(_text(reviewed.get("kind"), "mapping.kind"))
        semantic_type = reviewed.get("semantic_type")
        mappings.append(
            ReviewedWaitingPeriodMapping(
                normative_unit_id=unit_id,
                kind=mapping_kind,
                reason=_text(reviewed.get("reason"), "mapping.reason"),
                semantic_type=(
                    WaitingPeriodSemanticType(_text(semantic_type, "semantic_type"))
                    if semantic_type is not None
                    else None
                ),
                semantic_value=reviewed.get("semantic_value"),
            )
        )

    inventory = NormativeInventory(
        concept="waiting_periods",
        inventory_method="governed_migration_record",
        inventory_version=_text(record.get("inventory_version"), "inventory_version"),
        review_status=InventoryReviewStatus.REVIEWED,
        units=tuple(units),
    )
    mapped = map_reviewed_waiting_period_units(
        inventory.units,
        mappings,
        ontology_version=ontology_version,
    )
    accounting = account_normative_inventory(
        inventory,
        decisions=mapped.accounting_decisions,
        semantic_facts=mapped.semantic_facts,
        relationship_facts=mapped.relationship_facts,
    )
    return WaitingPeriodMigrationResult(
        applicability=applicability,
        source_document_id=document_id,
        source_document_version=document_version,
        source_hash_sha256=source_hash,
        ontology_version=ontology_version,
        review_decision_version=review_decision_version,
        mapping=mapped,
        accounting=accounting,
    )


__all__ = [
    "WaitingPeriodMigrationError",
    "WaitingPeriodMigrationResult",
    "migrate_waiting_period_record",
]
