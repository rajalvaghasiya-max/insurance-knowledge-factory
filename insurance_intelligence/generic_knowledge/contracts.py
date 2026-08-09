"""Generic cross-cutting knowledge contracts for MO-028B.G1.

These contracts are deliberately product-agnostic. They model applicability, source-anchored
normative units, semantic facts, relationship facts, residue accounting, and publication
blockers. They must never branch on insurer or product identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, Mapping


class GenericKnowledgeContractError(ValueError):
    """Raised when a generic knowledge contract is invalid."""


class NormativeUnitKind(str, Enum):
    OBLIGATION = "OBLIGATION"
    EXCLUSION = "EXCLUSION"
    CONDITION = "CONDITION"
    EXCEPTION = "EXCEPTION"
    MODIFICATION = "MODIFICATION"
    APPLICABILITY = "APPLICABILITY"
    RELATIONSHIP = "RELATIONSHIP"
    DEFINITION = "DEFINITION"
    OTHER_NORMATIVE = "OTHER_NORMATIVE"


class AccountingState(str, Enum):
    MAPPED = "MAPPED"
    MAPPED_AS_RELATIONSHIP = "MAPPED_AS_RELATIONSHIP"
    EXPLICITLY_NON_APPLICABLE = "EXPLICITLY_NON_APPLICABLE"
    DUPLICATE_CORROBORATING = "DUPLICATE_CORROBORATING"
    DEFERRED_WITH_REASON = "DEFERRED_WITH_REASON"
    NOT_YET_REPRESENTABLE = "NOT_YET_REPRESENTABLE"
    CONFLICTED = "CONFLICTED"


class RelationshipType(str, Enum):
    MODIFIES = "MODIFIES"
    WAIVES = "WAIVES"
    OVERRIDES = "OVERRIDES"
    DEPENDS_ON = "DEPENDS_ON"
    APPLIES_WHEN = "APPLIES_WHEN"
    INTERACTS_WITH = "INTERACTS_WITH"
    LIMITED_BY = "LIMITED_BY"


class PublicationBlockerCode(str, Enum):
    MATERIAL_RESIDUE = "MATERIAL_RESIDUE"
    NOT_YET_REPRESENTABLE = "NOT_YET_REPRESENTABLE"
    AUTHORITY_CONFLICT = "AUTHORITY_CONFLICT"
    SOURCE_STALE = "SOURCE_STALE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REGULATORY_CONFLICT = "REGULATORY_CONFLICT"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GenericKnowledgeContractError(f"{field_name} must be non-empty text")
    return value.strip()


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _text(value, field_name)


def _date_range_ok(start: date | None, end: date | None, field_name: str) -> None:
    if start is not None and not isinstance(start, date):
        raise GenericKnowledgeContractError(f"{field_name}.effective_from must be a date")
    if end is not None and not isinstance(end, date):
        raise GenericKnowledgeContractError(f"{field_name}.effective_to must be a date")
    if start is not None and end is not None and end < start:
        raise GenericKnowledgeContractError(f"{field_name}.effective_to cannot precede effective_from")


@dataclass(frozen=True)
class ApplicabilityKey:
    product_reference: str
    policy_version: str | None = None
    variant: str | None = None
    zone: str | None = None
    sum_insured_band: str | None = None
    optional_cover_state: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "product_reference", _text(self.product_reference, "product_reference"))
        for field_name in (
            "policy_version",
            "variant",
            "zone",
            "sum_insured_band",
            "optional_cover_state",
        ):
            object.__setattr__(self, field_name, _optional_text(getattr(self, field_name), field_name))
        _date_range_ok(self.effective_from, self.effective_to, "applicability")


@dataclass(frozen=True)
class EvidenceReference:
    evidence_id: str
    source_document_id: str
    source_document_version: str | None
    source_hash_sha256: str
    locator: str
    authority_class: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_id", _text(self.evidence_id, "evidence_id"))
        object.__setattr__(self, "source_document_id", _text(self.source_document_id, "source_document_id"))
        object.__setattr__(self, "source_document_version", _optional_text(self.source_document_version, "source_document_version"))
        object.__setattr__(self, "source_hash_sha256", _text(self.source_hash_sha256, "source_hash_sha256"))
        object.__setattr__(self, "locator", _text(self.locator, "locator"))
        object.__setattr__(self, "authority_class", _text(self.authority_class, "authority_class"))


@dataclass(frozen=True)
class NormativeUnit:
    normative_unit_id: str
    concept: str
    kind: NormativeUnitKind
    text_sha256: str
    excerpt: str
    applicability: ApplicabilityKey
    evidence: EvidenceReference
    materially_affects: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "normative_unit_id", _text(self.normative_unit_id, "normative_unit_id"))
        object.__setattr__(self, "concept", _text(self.concept, "concept"))
        object.__setattr__(self, "text_sha256", _text(self.text_sha256, "text_sha256"))
        object.__setattr__(self, "excerpt", _text(self.excerpt, "excerpt"))
        if not isinstance(self.kind, NormativeUnitKind):
            raise GenericKnowledgeContractError("kind must be a NormativeUnitKind")
        if not isinstance(self.applicability, ApplicabilityKey):
            raise GenericKnowledgeContractError("applicability must be an ApplicabilityKey")
        if not isinstance(self.evidence, EvidenceReference):
            raise GenericKnowledgeContractError("evidence must be an EvidenceReference")
        normalized = tuple(_text(value, "materially_affects") for value in self.materially_affects)
        if not normalized:
            raise GenericKnowledgeContractError("materially_affects must contain at least one insurance consequence")
        object.__setattr__(self, "materially_affects", normalized)


@dataclass(frozen=True)
class SemanticFact:
    fact_id: str
    concept: str
    semantic_type: str
    value: Mapping[str, Any]
    applicability: ApplicabilityKey
    evidence_ids: tuple[str, ...]
    ontology_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "fact_id", _text(self.fact_id, "fact_id"))
        object.__setattr__(self, "concept", _text(self.concept, "concept"))
        object.__setattr__(self, "semantic_type", _text(self.semantic_type, "semantic_type"))
        object.__setattr__(self, "ontology_version", _text(self.ontology_version, "ontology_version"))
        if not isinstance(self.value, Mapping) or not self.value:
            raise GenericKnowledgeContractError("value must be a non-empty mapping")
        if not isinstance(self.applicability, ApplicabilityKey):
            raise GenericKnowledgeContractError("applicability must be an ApplicabilityKey")
        evidence_ids = tuple(_text(value, "evidence_ids") for value in self.evidence_ids)
        if not evidence_ids:
            raise GenericKnowledgeContractError("evidence_ids must not be empty")
        object.__setattr__(self, "evidence_ids", evidence_ids)


@dataclass(frozen=True)
class RelationshipFact:
    relationship_id: str
    source_concept: str
    relationship_type: RelationshipType
    target_concept: str
    condition: Mapping[str, Any]
    applicability: ApplicabilityKey
    evidence_ids: tuple[str, ...]
    ontology_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "relationship_id", _text(self.relationship_id, "relationship_id"))
        object.__setattr__(self, "source_concept", _text(self.source_concept, "source_concept"))
        object.__setattr__(self, "target_concept", _text(self.target_concept, "target_concept"))
        object.__setattr__(self, "ontology_version", _text(self.ontology_version, "ontology_version"))
        if not isinstance(self.relationship_type, RelationshipType):
            raise GenericKnowledgeContractError("relationship_type must be a RelationshipType")
        if not isinstance(self.condition, Mapping):
            raise GenericKnowledgeContractError("condition must be a mapping")
        if not isinstance(self.applicability, ApplicabilityKey):
            raise GenericKnowledgeContractError("applicability must be an ApplicabilityKey")
        evidence_ids = tuple(_text(value, "evidence_ids") for value in self.evidence_ids)
        if not evidence_ids:
            raise GenericKnowledgeContractError("evidence_ids must not be empty")
        object.__setattr__(self, "evidence_ids", evidence_ids)


@dataclass(frozen=True)
class ResidueRecord:
    residue_id: str
    normative_unit_id: str
    concept: str
    applicability: ApplicabilityKey
    accounting_state: AccountingState
    reason: str
    material: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "residue_id", _text(self.residue_id, "residue_id"))
        object.__setattr__(self, "normative_unit_id", _text(self.normative_unit_id, "normative_unit_id"))
        object.__setattr__(self, "concept", _text(self.concept, "concept"))
        object.__setattr__(self, "reason", _text(self.reason, "reason"))
        if not isinstance(self.applicability, ApplicabilityKey):
            raise GenericKnowledgeContractError("applicability must be an ApplicabilityKey")
        if not isinstance(self.accounting_state, AccountingState):
            raise GenericKnowledgeContractError("accounting_state must be an AccountingState")
        if type(self.material) is not bool:
            raise GenericKnowledgeContractError("material must be boolean")


@dataclass(frozen=True)
class PublicationBlocker:
    blocker_id: str
    code: PublicationBlockerCode
    concept: str
    applicability: ApplicabilityKey
    reason: str
    normative_unit_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "blocker_id", _text(self.blocker_id, "blocker_id"))
        object.__setattr__(self, "concept", _text(self.concept, "concept"))
        object.__setattr__(self, "reason", _text(self.reason, "reason"))
        if not isinstance(self.code, PublicationBlockerCode):
            raise GenericKnowledgeContractError("code must be a PublicationBlockerCode")
        if not isinstance(self.applicability, ApplicabilityKey):
            raise GenericKnowledgeContractError("applicability must be an ApplicabilityKey")
        object.__setattr__(
            self,
            "normative_unit_ids",
            tuple(_text(value, "normative_unit_ids") for value in self.normative_unit_ids),
        )


def blocker_for_residue(residue: ResidueRecord) -> PublicationBlocker | None:
    """Return a typed blocker for material fail-closed residue, otherwise ``None``."""
    if not isinstance(residue, ResidueRecord):
        raise GenericKnowledgeContractError("residue must be a ResidueRecord")
    if not residue.material:
        return None
    if residue.accounting_state is AccountingState.NOT_YET_REPRESENTABLE:
        code = PublicationBlockerCode.NOT_YET_REPRESENTABLE
    elif residue.accounting_state is AccountingState.CONFLICTED:
        code = PublicationBlockerCode.AUTHORITY_CONFLICT
    elif residue.accounting_state in (
        AccountingState.MAPPED,
        AccountingState.MAPPED_AS_RELATIONSHIP,
        AccountingState.EXPLICITLY_NON_APPLICABLE,
        AccountingState.DUPLICATE_CORROBORATING,
    ):
        return None
    else:
        code = PublicationBlockerCode.MATERIAL_RESIDUE
    return PublicationBlocker(
        blocker_id=f"blocker_{residue.residue_id}",
        code=code,
        concept=residue.concept,
        applicability=residue.applicability,
        reason=residue.reason,
        normative_unit_ids=(residue.normative_unit_id,),
    )


__all__ = [
    "AccountingState",
    "ApplicabilityKey",
    "EvidenceReference",
    "GenericKnowledgeContractError",
    "NormativeUnit",
    "NormativeUnitKind",
    "PublicationBlocker",
    "PublicationBlockerCode",
    "RelationshipFact",
    "RelationshipType",
    "ResidueRecord",
    "SemanticFact",
    "blocker_for_residue",
]
