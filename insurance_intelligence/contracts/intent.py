"""Versioned, executable contracts for the Intent Analyzer (MO-013).

Follows the repository's existing validation convention: frozen
dataclasses constructed only through validating factory functions,
matching the pattern already used throughout factory_core/ (e.g.
ProductIdentityReferenceResult, MigrationManifest). No new
dependency is introduced.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from insurance_intelligence.intent.taxonomy import (
    GOVERNED_INTENT_LABELS,
    validate_intent_label,
)

SUPPORTED_CONTRACT_VERSION = "1.0"

DOMAIN_VALUES = frozenset({"health", "motor", "life", "claims", "unknown"})
LANGUAGE_VALUES = frozenset({"en", "unknown"})

CANDIDATE_ENTITY_TYPES = frozenset(
    {
        "INSURER",
        "PRODUCT",
        "POLICY_FEATURE",
        "DOCUMENT_TYPE",
        "CLAIM_CONCEPT",
        "FINANCIAL_VALUE",
        "AGE",
        "TIME_PERIOD",
        "UNKNOWN",
    }
)

AMBIGUITY_TYPES = frozenset(
    {
        "MISSING_SUBJECT",
        "MULTIPLE_POSSIBLE_SUBJECTS",
        "UNRESOLVED_PRONOUN",
        "MISSING_COMPARISON_TARGET",
        "UNCLEAR_REQUESTED_OUTCOME",
        "DOMAIN_AMBIGUITY",
        "INSUFFICIENT_FOLLOW_UP_CONTEXT",
    }
)

ANALYSIS_STATUS_VALUES = frozenset(
    {
        "CLASSIFIED",
        "CLASSIFIED_WITH_AMBIGUITY",
        "CLARIFICATION_REQUIRED",
        "OUT_OF_SCOPE",
        "INVALID_REQUEST",
    }
)

CLASSIFICATION_BASIS_VALUES = frozenset(
    {
        "matched_phrase",
        "matched_term",
        "conversation_reference",
        "question_pattern",
        "domain_keyword",
        "fallback_rule",
    }
)

FOLLOW_UP_REFERENCE_TYPES = frozenset(
    {
        "prior_candidate_entity",
        "prior_topic",
        "none",
    }
)


class IntentAnalyzerError(ValueError):
    """Raised when a contract value is structurally or semantically invalid."""


def _require_nonempty_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IntentAnalyzerError(f"{label} must be a non-empty string")
    return value


def _require_str(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise IntentAnalyzerError(f"{label} must be a string")
    return value


def _require_bounded_float(value: object, label: str, *, low: float = 0.0, high: float = 1.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise IntentAnalyzerError(f"{label} must be a number")
    numeric = float(value)
    if not (low <= numeric <= high):
        raise IntentAnalyzerError(f"{label} must be between {low} and {high}; got {numeric}")
    return numeric


def _require_member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise IntentAnalyzerError(f"{label} must be one of {sorted(allowed)}; got {value!r}")
    return value  # type: ignore[return-value]


# --- Conversation context ---------------------------------------------------


@dataclass(frozen=True)
class ConversationItem:
    role: str
    text: str
    sequence: int


def build_conversation_item(raw: Mapping[str, Any]) -> ConversationItem:
    role = _require_member(raw.get("role"), frozenset({"user", "system"}), "conversation_context[].role")
    text = _require_str(raw.get("text"), "conversation_context[].text")
    sequence = raw.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int):
        raise IntentAnalyzerError("conversation_context[].sequence must be an integer")
    return ConversationItem(role=role, text=text, sequence=sequence)


# --- Known entity mentions (input, for follow-up continuity) ---------------


@dataclass(frozen=True)
class KnownEntityMention:
    entity_type: str
    surface_text: str
    normalized_text: str


def build_known_entity_mention(raw: Mapping[str, Any]) -> KnownEntityMention:
    entity_type = _require_member(raw.get("entity_type"), CANDIDATE_ENTITY_TYPES, "known_entity_mentions[].entity_type")
    surface_text = _require_nonempty_str(raw.get("surface_text"), "known_entity_mentions[].surface_text")
    normalized_text = _require_nonempty_str(raw.get("normalized_text"), "known_entity_mentions[].normalized_text")
    return KnownEntityMention(entity_type=entity_type, surface_text=surface_text, normalized_text=normalized_text)


# --- Input contract ----------------------------------------------------------


@dataclass(frozen=True)
class IntentAnalyzerInput:
    contract_version: str
    request_id: str
    text: str
    domain_hint: str
    conversation_context: tuple[ConversationItem, ...]
    known_entity_mentions: tuple[KnownEntityMention, ...]
    language: str


def build_input(
    *,
    request_id: str,
    text: str,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
    domain_hint: str = "unknown",
    conversation_context: Sequence[Mapping[str, Any]] = (),
    known_entity_mentions: Sequence[Mapping[str, Any]] = (),
    language: str = "en",
) -> IntentAnalyzerInput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise IntentAnalyzerError(
            f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}; got {contract_version!r}"
        )
    validated_request_id = _require_nonempty_str(request_id, "request_id")
    if not isinstance(text, str):
        raise IntentAnalyzerError("text must be a string")
    validated_domain_hint = _require_member(domain_hint, DOMAIN_VALUES, "domain_hint")
    validated_language = _require_member(language, LANGUAGE_VALUES, "language")
    validated_context = tuple(build_conversation_item(item) for item in conversation_context)
    validated_mentions = tuple(build_known_entity_mention(item) for item in known_entity_mentions)
    return IntentAnalyzerInput(
        contract_version=contract_version,
        request_id=validated_request_id,
        text=text,
        domain_hint=validated_domain_hint,
        conversation_context=validated_context,
        known_entity_mentions=validated_mentions,
        language=validated_language,
    )


# --- Output contract ---------------------------------------------------------


@dataclass(frozen=True)
class CandidateEntity:
    entity_type: str
    surface_text: str
    normalized_text: str
    source: str
    confidence: float


@dataclass(frozen=True)
class Ambiguity:
    ambiguity_type: str
    description: str
    materiality: str


@dataclass(frozen=True)
class FollowUp:
    is_follow_up: bool
    reference_type: str
    referenced_text: str
    confidence: float


@dataclass(frozen=True)
class IntentAnalyzerOutput:
    contract_version: str
    request_id: str
    primary_intent: str
    secondary_intents: tuple[str, ...]
    domain: str
    candidate_entities: tuple[CandidateEntity, ...]
    requested_outcome: str
    ambiguities: tuple[Ambiguity, ...]
    follow_up: FollowUp
    confidence: float
    classification_basis: tuple[str, ...]
    analysis_status: str
    clarification_question: str | None


def build_candidate_entity(
    *, entity_type: str, surface_text: str, normalized_text: str, source: str, confidence: float
) -> CandidateEntity:
    validated_type = _require_member(entity_type, CANDIDATE_ENTITY_TYPES, "candidate_entities[].entity_type")
    validated_surface = _require_nonempty_str(surface_text, "candidate_entities[].surface_text")
    validated_normalized = _require_nonempty_str(normalized_text, "candidate_entities[].normalized_text")
    validated_source = _require_nonempty_str(source, "candidate_entities[].source")
    validated_confidence = _require_bounded_float(confidence, "candidate_entities[].confidence")
    return CandidateEntity(
        entity_type=validated_type,
        surface_text=validated_surface,
        normalized_text=validated_normalized,
        source=validated_source,
        confidence=validated_confidence,
    )


def build_ambiguity(*, ambiguity_type: str, description: str, materiality: str) -> Ambiguity:
    validated_type = _require_member(ambiguity_type, AMBIGUITY_TYPES, "ambiguities[].ambiguity_type")
    validated_description = _require_nonempty_str(description, "ambiguities[].description")
    validated_materiality = _require_member(
        materiality, frozenset({"low", "medium", "high"}), "ambiguities[].materiality"
    )
    return Ambiguity(ambiguity_type=validated_type, description=validated_description, materiality=validated_materiality)


def build_follow_up(
    *, is_follow_up: bool, reference_type: str = "none", referenced_text: str = "", confidence: float = 0.0
) -> FollowUp:
    if not isinstance(is_follow_up, bool):
        raise IntentAnalyzerError("follow_up.is_follow_up must be a boolean")
    validated_reference_type = _require_member(reference_type, FOLLOW_UP_REFERENCE_TYPES, "follow_up.reference_type")
    validated_referenced_text = _require_str(referenced_text, "follow_up.referenced_text")
    validated_confidence = _require_bounded_float(confidence, "follow_up.confidence")
    return FollowUp(
        is_follow_up=is_follow_up,
        reference_type=validated_reference_type,
        referenced_text=validated_referenced_text,
        confidence=validated_confidence,
    )


def build_output(
    *,
    request_id: str,
    primary_intent: str,
    domain: str,
    requested_outcome: str,
    confidence: float,
    analysis_status: str,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
    secondary_intents: Sequence[str] = (),
    candidate_entities: Sequence[CandidateEntity] = (),
    ambiguities: Sequence[Ambiguity] = (),
    follow_up: FollowUp | None = None,
    classification_basis: Sequence[str] = (),
    clarification_question: str | None = None,
) -> IntentAnalyzerOutput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise IntentAnalyzerError(
            f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}; got {contract_version!r}"
        )
    validated_request_id = _require_nonempty_str(request_id, "request_id")
    validated_primary = validate_intent_label(primary_intent, field_label="primary_intent")

    validated_secondary: list[str] = []
    for label in secondary_intents:
        validated = validate_intent_label(label, field_label="secondary_intents[]")
        if validated == validated_primary:
            raise IntentAnalyzerError("primary_intent must not be duplicated in secondary_intents")
        if validated in validated_secondary:
            raise IntentAnalyzerError(f"secondary_intents must be unique; duplicate {validated!r}")
        validated_secondary.append(validated)

    validated_domain = _require_member(domain, DOMAIN_VALUES, "domain")
    validated_outcome = _require_str(requested_outcome, "requested_outcome")
    validated_confidence = _require_bounded_float(confidence, "confidence")
    validated_status = _require_member(analysis_status, ANALYSIS_STATUS_VALUES, "analysis_status")

    validated_basis: list[str] = []
    for basis in classification_basis:
        validated_basis.append(_require_member(basis, CLASSIFICATION_BASIS_VALUES, "classification_basis[]"))

    if validated_status == "CLARIFICATION_REQUIRED":
        if not clarification_question or not clarification_question.strip():
            raise IntentAnalyzerError("clarification_question is required when analysis_status is CLARIFICATION_REQUIRED")
    else:
        if clarification_question is not None:
            raise IntentAnalyzerError(
                "clarification_question must be absent/null unless analysis_status is CLARIFICATION_REQUIRED"
            )

    resolved_follow_up = follow_up if follow_up is not None else build_follow_up(is_follow_up=False)

    return IntentAnalyzerOutput(
        contract_version=contract_version,
        request_id=validated_request_id,
        primary_intent=validated_primary,
        secondary_intents=tuple(validated_secondary),
        domain=validated_domain,
        candidate_entities=tuple(candidate_entities),
        requested_outcome=validated_outcome,
        ambiguities=tuple(ambiguities),
        follow_up=resolved_follow_up,
        confidence=validated_confidence,
        classification_basis=tuple(validated_basis),
        analysis_status=validated_status,
        clarification_question=clarification_question if validated_status == "CLARIFICATION_REQUIRED" else None,
    )


assert GOVERNED_INTENT_LABELS  # imported for validation; referenced to avoid unused-import lint noise
