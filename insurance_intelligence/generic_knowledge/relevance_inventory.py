"""Generic concept-relevance envelope and high-recall inventory interface for MO-028B.G4.

The engine in this module is concept- and product-agnostic.  Concept policy supplies reusable
inventory rules; source adapters supply normalized source fragments.  The engine conservatively
selects fragments that may carry normative consequences and emits source-anchored ``NormativeUnit``
values for G3 accounting.  Product identity appears only inside ``ApplicabilityKey`` data.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Iterable, Sequence

from insurance_intelligence.generic_knowledge.contracts import (
    ApplicabilityKey,
    EvidenceReference,
    GenericKnowledgeContractError,
    NormativeUnit,
    NormativeUnitKind,
)
from insurance_intelligence.generic_knowledge.normative_inventory import (
    InventoryReviewStatus,
    NormativeInventory,
)


class RelevanceInventoryError(GenericKnowledgeContractError):
    """Raised when relevance-envelope or inventory inputs are invalid."""


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RelevanceInventoryError(f"{field_name} must be non-empty text")
    return value.strip()


@dataclass(frozen=True)
class SourceFragment:
    """Normalized source text supplied by any evidence-source adapter."""

    fragment_id: str
    text: str
    locator: str
    source_class: str
    applicability: ApplicabilityKey
    evidence: EvidenceReference

    def __post_init__(self) -> None:
        object.__setattr__(self, "fragment_id", _text(self.fragment_id, "fragment_id"))
        object.__setattr__(self, "text", _text(self.text, "text"))
        object.__setattr__(self, "locator", _text(self.locator, "locator"))
        object.__setattr__(self, "source_class", _text(self.source_class, "source_class"))
        if not isinstance(self.applicability, ApplicabilityKey):
            raise RelevanceInventoryError("applicability must be an ApplicabilityKey")
        if not isinstance(self.evidence, EvidenceReference):
            raise RelevanceInventoryError("evidence must be an EvidenceReference")
        if self.evidence.locator != self.locator:
            raise RelevanceInventoryError("evidence locator must match fragment locator")


@dataclass(frozen=True)
class InventoryRule:
    """Reusable concept-policy rule for conservative normative selection."""

    rule_id: str
    anchors: tuple[str, ...]
    kind: NormativeUnitKind
    materially_affects: tuple[str, ...]
    allowed_source_classes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", _text(self.rule_id, "rule_id"))
        anchors = tuple(_text(value, "anchors") for value in self.anchors)
        if not anchors:
            raise RelevanceInventoryError("anchors must contain at least one value")
        object.__setattr__(self, "anchors", anchors)
        if not isinstance(self.kind, NormativeUnitKind):
            raise RelevanceInventoryError("kind must be a NormativeUnitKind")
        consequences = tuple(_text(value, "materially_affects") for value in self.materially_affects)
        if not consequences:
            raise RelevanceInventoryError(
                "materially_affects must contain at least one insurance consequence"
            )
        object.__setattr__(self, "materially_affects", consequences)
        object.__setattr__(
            self,
            "allowed_source_classes",
            tuple(_text(value, "allowed_source_classes") for value in self.allowed_source_classes),
        )


@dataclass(frozen=True)
class ConceptRelevanceEnvelope:
    concept: str
    policy_version: str
    rules: tuple[InventoryRule, ...]
    required_source_classes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "concept", _text(self.concept, "concept"))
        object.__setattr__(self, "policy_version", _text(self.policy_version, "policy_version"))
        if not self.rules:
            raise RelevanceInventoryError("rules must contain at least one InventoryRule")
        seen: set[str] = set()
        for rule in self.rules:
            if not isinstance(rule, InventoryRule):
                raise RelevanceInventoryError("rules must contain InventoryRule values")
            if rule.rule_id in seen:
                raise RelevanceInventoryError(f"duplicate rule_id: {rule.rule_id}")
            seen.add(rule.rule_id)
        object.__setattr__(
            self,
            "required_source_classes",
            tuple(_text(value, "required_source_classes") for value in self.required_source_classes),
        )


@dataclass(frozen=True)
class InventorySelection:
    normative_unit: NormativeUnit
    matched_rule_ids: tuple[str, ...]
    matched_anchors: tuple[str, ...]


@dataclass(frozen=True)
class HighRecallInventoryResult:
    inventory: NormativeInventory
    selections: tuple[InventorySelection, ...]
    observed_source_classes: tuple[str, ...]
    missing_required_source_classes: tuple[str, ...]

    @property
    def source_envelope_complete(self) -> bool:
        return not self.missing_required_source_classes


def _matches(rule: InventoryRule, fragment: SourceFragment) -> tuple[str, ...]:
    if rule.allowed_source_classes and fragment.source_class not in rule.allowed_source_classes:
        return ()
    haystack = fragment.text.casefold()
    return tuple(anchor for anchor in rule.anchors if anchor.casefold() in haystack)


def _unit_id(concept: str, fragment: SourceFragment) -> str:
    digest = hashlib.sha256(
        f"{concept}|{fragment.evidence.source_document_id}|{fragment.fragment_id}|{fragment.locator}|{fragment.text}".encode(
            "utf-8"
        )
    ).hexdigest()[:24]
    return f"norm_{digest}"


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def inventory_from_fragments(
    envelope: ConceptRelevanceEnvelope,
    fragments: Sequence[SourceFragment],
    *,
    inventory_method: str = "concept_relevance_envelope_high_recall",
    review_status: InventoryReviewStatus = InventoryReviewStatus.UNREVIEWED,
) -> HighRecallInventoryResult:
    """Build a conservative source-anchored normative inventory.

    Any fragment matching one or more reusable concept-policy rules is retained exactly once.
    Consequences are unioned across all matching rules so one clause can expose multiple material
    effects.  This function intentionally does not map text into semantic facts.
    """
    if not isinstance(envelope, ConceptRelevanceEnvelope):
        raise RelevanceInventoryError("envelope must be a ConceptRelevanceEnvelope")
    if not isinstance(review_status, InventoryReviewStatus):
        raise RelevanceInventoryError("review_status must be an InventoryReviewStatus")
    inventory_method = _text(inventory_method, "inventory_method")

    observed_source_classes: set[str] = set()
    selections: list[InventorySelection] = []
    seen_fragment_ids: set[str] = set()

    for fragment in fragments:
        if not isinstance(fragment, SourceFragment):
            raise RelevanceInventoryError("fragments must contain SourceFragment values")
        if fragment.fragment_id in seen_fragment_ids:
            raise RelevanceInventoryError(f"duplicate fragment_id: {fragment.fragment_id}")
        seen_fragment_ids.add(fragment.fragment_id)
        observed_source_classes.add(fragment.source_class)

        matches: list[tuple[InventoryRule, tuple[str, ...]]] = []
        for rule in envelope.rules:
            anchors = _matches(rule, fragment)
            if anchors:
                matches.append((rule, anchors))
        if not matches:
            continue

        kinds = {rule.kind for rule, _ in matches}
        # A fragment can legitimately contain several normative effects.  Preserve the most
        # conservative generic kind when rules disagree rather than pretending one interpretation
        # is definitive at inventory time.
        kind = next(iter(kinds)) if len(kinds) == 1 else NormativeUnitKind.OTHER_NORMATIVE
        consequences = tuple(
            sorted({value for rule, _ in matches for value in rule.materially_affects})
        )
        matched_rule_ids = tuple(sorted(rule.rule_id for rule, _ in matches))
        matched_anchors = tuple(sorted({anchor for _, anchors in matches for anchor in anchors}))

        unit = NormativeUnit(
            normative_unit_id=_unit_id(envelope.concept, fragment),
            concept=envelope.concept,
            kind=kind,
            text_sha256=_text_sha256(fragment.text),
            excerpt=fragment.text,
            applicability=fragment.applicability,
            evidence=fragment.evidence,
            materially_affects=consequences,
        )
        selections.append(
            InventorySelection(
                normative_unit=unit,
                matched_rule_ids=matched_rule_ids,
                matched_anchors=matched_anchors,
            )
        )

    if not selections:
        raise RelevanceInventoryError(
            "high-recall inventory produced no normative units for the concept envelope"
        )

    selections.sort(key=lambda item: item.normative_unit.normative_unit_id)
    inventory = NormativeInventory(
        concept=envelope.concept,
        inventory_method=inventory_method,
        inventory_version=envelope.policy_version,
        review_status=review_status,
        units=tuple(item.normative_unit for item in selections),
    )
    missing = tuple(
        sorted(set(envelope.required_source_classes) - observed_source_classes)
    )
    return HighRecallInventoryResult(
        inventory=inventory,
        selections=tuple(selections),
        observed_source_classes=tuple(sorted(observed_source_classes)),
        missing_required_source_classes=missing,
    )


__all__ = [
    "ConceptRelevanceEnvelope",
    "HighRecallInventoryResult",
    "InventoryRule",
    "InventorySelection",
    "RelevanceInventoryError",
    "SourceFragment",
    "inventory_from_fragments",
]
