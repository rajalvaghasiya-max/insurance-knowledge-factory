"""HC-1.0 contracts for the Health Domain Knowledge & Semantic Gap Registry.

The registry is intentionally a gap ledger, not a completion dashboard. Domain
knowledge and product semantics are separate axes, claim-aspects are placed in
planes contextually, and unknown semantic variant space is permanently open.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HealthDomainRegistryError(ValueError):
    """Raised when a HC-1 registry record violates an architectural invariant."""


def _text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HealthDomainRegistryError(f"{field_name} must be non-empty text")
    return value.strip()


class KnowledgePlane(str, Enum):
    REGULATORY_LIFECYCLE = "RegulatoryLifecycle"
    PRODUCT_MECHANIC = "ProductMechanic"
    CLAIMS_OPERATIONAL = "ClaimsOperational"


class DomainKnowledgeMaturity(str, Enum):
    DK0_UNCATALOGUED = "DK0_UNCATALOGUED"
    DK1_AUTHORITATIVE_DEFINITION_AVAILABLE = "DK1_AUTHORITATIVE_DEFINITION_AVAILABLE"
    DK2_CONCEPT_BOUNDARY_DEFINED = "DK2_CONCEPT_BOUNDARY_DEFINED"
    DK3_EXPLANATION_READY = "DK3_EXPLANATION_READY"


class ProductSemanticMaturity(str, Enum):
    PS0_UNOBSERVED = "PS0_UNOBSERVED"
    PS1_EVIDENCE_OBSERVED = "PS1_EVIDENCE_OBSERVED"
    PS2_REPRESENTABLE = "PS2_REPRESENTABLE"
    PS3_EVIDENCE_BINDABLE = "PS3_EVIDENCE_BINDABLE"
    PS4_CERTIFIED = "PS4_CERTIFIED"
    PS5_REASONING_VALIDATED = "PS5_REASONING_VALIDATED"


class SemanticBlockingState(str, Enum):
    REPRESENTATION_GAP = "REPRESENTATION_GAP"
    KNOWLEDGE_GAP = "KNOWLEDGE_GAP"
    CONFLICT = "CONFLICT"
    CURRENTNESS_UNRESOLVED = "CURRENTNESS_UNRESOLVED"
    POLICY_CONTEXT_REQUIRED = "POLICY_CONTEXT_REQUIRED"


@dataclass(frozen=True)
class ClaimAspect:
    """One claim-shaped aspect of a concept assigned to its governing plane."""

    aspect_id: str
    concept_id: str
    plane: KnowledgePlane
    claim_type: str
    authority_context: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "aspect_id", _text(self.aspect_id, "aspect_id"))
        object.__setattr__(self, "concept_id", _text(self.concept_id, "concept_id"))
        object.__setattr__(self, "claim_type", _text(self.claim_type, "claim_type"))
        object.__setattr__(
            self, "authority_context", _text(self.authority_context, "authority_context")
        )
        if not isinstance(self.plane, KnowledgePlane):
            raise HealthDomainRegistryError("plane must be a KnowledgePlane")


@dataclass(frozen=True)
class DomainKnowledgeRecord:
    concept_id: str
    maturity: DomainKnowledgeMaturity
    authoritative_definition_refs: tuple[str, ...] = ()
    boundary_notes: tuple[str, ...] = ()
    unknown_variant_space_open: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "concept_id", _text(self.concept_id, "concept_id"))
        if not isinstance(self.maturity, DomainKnowledgeMaturity):
            raise HealthDomainRegistryError("maturity must be DomainKnowledgeMaturity")
        if self.unknown_variant_space_open is not True:
            raise HealthDomainRegistryError(
                "unknown_variant_space_open is permanently true and cannot be closed"
            )
        if self.maturity is DomainKnowledgeMaturity.DK0_UNCATALOGUED:
            if self.authoritative_definition_refs or self.boundary_notes:
                raise HealthDomainRegistryError(
                    "DK0_UNCATALOGUED cannot carry authoritative definitions or boundary notes"
                )
        if self.maturity in {
            DomainKnowledgeMaturity.DK1_AUTHORITATIVE_DEFINITION_AVAILABLE,
            DomainKnowledgeMaturity.DK2_CONCEPT_BOUNDARY_DEFINED,
            DomainKnowledgeMaturity.DK3_EXPLANATION_READY,
        } and not self.authoritative_definition_refs:
            raise HealthDomainRegistryError(
                "DK1+ requires at least one authoritative definition reference"
            )
        if self.maturity in {
            DomainKnowledgeMaturity.DK2_CONCEPT_BOUNDARY_DEFINED,
            DomainKnowledgeMaturity.DK3_EXPLANATION_READY,
        } and not self.boundary_notes:
            raise HealthDomainRegistryError("DK2+ requires boundary notes")


@dataclass(frozen=True)
class ProductSemanticRecord:
    concept_id: str
    semantic_variant_id: str
    product_reference: str
    product_version_reference: str
    maturity: ProductSemanticMaturity | None = None
    blocking_state: SemanticBlockingState | None = None
    evidence_reference_ids: tuple[str, ...] = ()
    unknown_variant_space_open: bool = True

    def __post_init__(self) -> None:
        for field_name in (
            "concept_id",
            "semantic_variant_id",
            "product_reference",
            "product_version_reference",
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        if self.unknown_variant_space_open is not True:
            raise HealthDomainRegistryError(
                "unknown_variant_space_open is permanently true and cannot be closed"
            )
        has_maturity = self.maturity is not None
        has_block = self.blocking_state is not None
        if has_maturity == has_block:
            raise HealthDomainRegistryError(
                "exactly one of maturity or blocking_state must be set"
            )
        if has_maturity and not isinstance(self.maturity, ProductSemanticMaturity):
            raise HealthDomainRegistryError("maturity must be ProductSemanticMaturity")
        if has_block and not isinstance(self.blocking_state, SemanticBlockingState):
            raise HealthDomainRegistryError("blocking_state must be SemanticBlockingState")
        if self.maturity in {
            ProductSemanticMaturity.PS1_EVIDENCE_OBSERVED,
            ProductSemanticMaturity.PS2_REPRESENTABLE,
            ProductSemanticMaturity.PS3_EVIDENCE_BINDABLE,
            ProductSemanticMaturity.PS4_CERTIFIED,
            ProductSemanticMaturity.PS5_REASONING_VALIDATED,
        } and not self.evidence_reference_ids:
            raise HealthDomainRegistryError("PS1+ requires evidence references")
        if self.blocking_state is SemanticBlockingState.REPRESENTATION_GAP and not self.evidence_reference_ids:
            raise HealthDomainRegistryError(
                "REPRESENTATION_GAP requires observed evidence references"
            )


def domain_knowledge_can_answer(*, instance_context_in_scope: bool) -> bool:
    """Hard HC-1 instance guard.

    Domain knowledge may support a general explanation only. Once any resolved
    policy/customer instance is in scope, product/operational evidence must take over.
    """

    if type(instance_context_in_scope) is not bool:
        raise HealthDomainRegistryError("instance_context_in_scope must be bool")
    return not instance_context_in_scope


__all__ = [
    "ClaimAspect",
    "DomainKnowledgeMaturity",
    "DomainKnowledgeRecord",
    "HealthDomainRegistryError",
    "KnowledgePlane",
    "ProductSemanticMaturity",
    "ProductSemanticRecord",
    "SemanticBlockingState",
    "domain_knowledge_can_answer",
]
