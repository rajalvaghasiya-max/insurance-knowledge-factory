"""Versioned, executable contracts for the Context Builder (MO-014).

Follows the same repository convention as intent.py: frozen
dataclasses constructed only through validating factory functions.
No new dependency.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from insurance_intelligence.contracts.intent import (
    ConversationItem,
    IntentAnalyzerOutput,
    build_conversation_item,
)

SUPPORTED_CONTRACT_VERSION = "1.0"

CONTEXT_CATEGORIES = frozenset(
    {
        "USER",
        "POLICY",
        "PRODUCT",
        "DOCUMENT",
        "CONVERSATION",
        "SCENARIO",
        "FINANCIAL",
        "TEMPORAL",
        "JURISDICTION",
        "DOMAIN",
    }
)

PROVENANCE_STATUSES = frozenset(
    {
        "USER_PROVIDED",
        "DOCUMENT_RESOLVED",
        "SYSTEM_DERIVED",
        "ASSUMED",
        "UNVERIFIED",
        "STALE",
        "SUPERSEDED",
    }
)

ITEM_STATUS_VALUES = frozenset({"ACTIVE", "SUPERSEDED"})

MATERIALITY_VALUES = frozenset({"low", "medium", "high"})

ANSWERABILITY_VALUES = frozenset(
    {
        "ANSWERABLE",
        "ANSWERABLE_WITH_ASSUMPTIONS",
        "PARTIALLY_ANSWERABLE",
        "CLARIFICATION_REQUIRED",
        "NOT_ANSWERABLE",
        "OUT_OF_SCOPE",
    }
)

CONFLICT_RESOLUTION_STATUSES = frozenset(
    {
        "UNRESOLVED",
        "RESOLVED_BY_RECENCY",
        "RESOLVED_BY_EXPLICIT_USER_CORRECTION",
        "SUPERSEDED",
    }
)

DOCUMENT_PROCESSING_STATUSES = frozenset({"PENDING", "PROCESSED", "FAILED", "UNAVAILABLE"})

CLASSIFICATION_BASIS_VALUES = frozenset(
    {
        "user_provided",
        "candidate_entity",
        "document_metadata",
        "session_context",
        "conversation_reference",
        "assumption",
        "fallback_rule",
    }
)


class ContextBuilderError(ValueError):
    """Raised when a context contract value is structurally or semantically invalid."""


def _require_nonempty_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContextBuilderError(f"{label} must be a non-empty string")
    return value


def _require_str(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ContextBuilderError(f"{label} must be a string")
    return value


def _require_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ContextBuilderError(f"{label} must be a boolean")
    return value


def _require_bounded_float(value: object, label: str, *, low: float = 0.0, high: float = 1.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContextBuilderError(f"{label} must be a number")
    numeric = float(value)
    if not (low <= numeric <= high):
        raise ContextBuilderError(f"{label} must be between {low} and {high}; got {numeric}")
    return numeric


def _require_member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise ContextBuilderError(f"{label} must be one of {sorted(allowed)}; got {value!r}")
    return value  # type: ignore[return-value]


def _require_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContextBuilderError(f"{label} must be an integer")
    return value


# --- Input sub-items ---------------------------------------------------------


@dataclass(frozen=True)
class UserContextItem:
    key: str
    value: str
    source_reference: str
    sequence: int


def build_user_context_item(raw: Mapping[str, Any]) -> UserContextItem:
    return UserContextItem(
        key=_require_nonempty_str(raw.get("key"), "user_context[].key"),
        value=_require_str(raw.get("value"), "user_context[].value"),
        source_reference=_require_nonempty_str(raw.get("source_reference"), "user_context[].source_reference"),
        sequence=_require_int(raw.get("sequence"), "user_context[].sequence"),
    )


@dataclass(frozen=True)
class DocumentContextItem:
    document_reference: str
    document_type: str
    processing_status: str
    candidate_entities: tuple[str, ...]


def build_document_context_item(raw: Mapping[str, Any]) -> DocumentContextItem:
    return DocumentContextItem(
        document_reference=_require_nonempty_str(raw.get("document_reference"), "document_context[].document_reference"),
        document_type=_require_str(raw.get("document_type"), "document_context[].document_type"),
        processing_status=_require_member(
            raw.get("processing_status"), DOCUMENT_PROCESSING_STATUSES, "document_context[].processing_status"
        ),
        candidate_entities=tuple(str(entity) for entity in raw.get("candidate_entities", ())),
    )


@dataclass(frozen=True)
class ResolvedContextItem:
    key: str
    value: str
    category: str
    provenance: str
    source_reference: str
    confidence: float
    status: str
    materiality: str


def build_resolved_context_item(
    *,
    key: str,
    value: str,
    category: str,
    provenance: str,
    source_reference: str,
    confidence: float,
    status: str = "ACTIVE",
    materiality: str = "medium",
) -> ResolvedContextItem:
    return ResolvedContextItem(
        key=_require_nonempty_str(key, "resolved_context[].key"),
        value=_require_str(value, "resolved_context[].value"),
        category=_require_member(category, CONTEXT_CATEGORIES, "resolved_context[].category"),
        provenance=_require_member(provenance, PROVENANCE_STATUSES, "resolved_context[].provenance"),
        source_reference=_require_nonempty_str(source_reference, "resolved_context[].source_reference"),
        confidence=_require_bounded_float(confidence, "resolved_context[].confidence"),
        status=_require_member(status, ITEM_STATUS_VALUES, "resolved_context[].status"),
        materiality=_require_member(materiality, MATERIALITY_VALUES, "resolved_context[].materiality"),
    )


# Session context items carry the same shape as resolved context items --
# they are previously-resolved context being carried forward.
SessionContextItem = ResolvedContextItem
build_session_context_item = build_resolved_context_item


# --- Input contract ----------------------------------------------------------


@dataclass(frozen=True)
class ContextBuilderInput:
    contract_version: str
    request_id: str
    intent_analysis: IntentAnalyzerOutput
    user_context: tuple[UserContextItem, ...]
    conversation_context: tuple[ConversationItem, ...]
    document_context: tuple[DocumentContextItem, ...]
    session_context: tuple[ResolvedContextItem, ...]


def build_input(
    *,
    request_id: str,
    intent_analysis: IntentAnalyzerOutput,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
    user_context: Sequence[Mapping[str, Any]] = (),
    conversation_context: Sequence[Mapping[str, Any]] = (),
    document_context: Sequence[Mapping[str, Any]] = (),
    session_context: Sequence[ResolvedContextItem] = (),
) -> ContextBuilderInput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise ContextBuilderError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}; got {contract_version!r}")
    if not isinstance(intent_analysis, IntentAnalyzerOutput):
        raise ContextBuilderError("intent_analysis must be a validated IntentAnalyzerOutput")
    validated_request_id = _require_nonempty_str(request_id, "request_id")
    return ContextBuilderInput(
        contract_version=contract_version,
        request_id=validated_request_id,
        intent_analysis=intent_analysis,
        user_context=tuple(build_user_context_item(item) for item in user_context),
        conversation_context=tuple(build_conversation_item(item) for item in conversation_context),
        document_context=tuple(build_document_context_item(item) for item in document_context),
        session_context=tuple(session_context),
    )


# --- Output sub-items ---------------------------------------------------------


@dataclass(frozen=True)
class MissingContextItem:
    key: str
    category: str
    required: bool
    materiality: str
    reason: str
    clarification_question: str


def build_missing_context_item(
    *, key: str, category: str, required: bool, materiality: str, reason: str, clarification_question: str
) -> MissingContextItem:
    return MissingContextItem(
        key=_require_nonempty_str(key, "missing_context[].key"),
        category=_require_member(category, CONTEXT_CATEGORIES, "missing_context[].category"),
        required=_require_bool(required, "missing_context[].required"),
        materiality=_require_member(materiality, MATERIALITY_VALUES, "missing_context[].materiality"),
        reason=_require_nonempty_str(reason, "missing_context[].reason"),
        clarification_question=_require_nonempty_str(
            clarification_question, "missing_context[].clarification_question"
        ),
    )


@dataclass(frozen=True)
class ContextConflict:
    key: str
    values: tuple[str, ...]
    source_references: tuple[str, ...]
    materiality: str
    resolution_status: str


def build_context_conflict(
    *, key: str, values: Sequence[str], source_references: Sequence[str], materiality: str, resolution_status: str
) -> ContextConflict:
    if len(values) < 2:
        raise ContextBuilderError("conflicts[].values must contain at least two distinct values")
    return ContextConflict(
        key=_require_nonempty_str(key, "conflicts[].key"),
        values=tuple(values),
        source_references=tuple(source_references),
        materiality=_require_member(materiality, MATERIALITY_VALUES, "conflicts[].materiality"),
        resolution_status=_require_member(
            resolution_status, CONFLICT_RESOLUTION_STATUSES, "conflicts[].resolution_status"
        ),
    )


@dataclass(frozen=True)
class Assumption:
    assumption_id: str
    key: str
    value: str
    reason: str
    materiality: str
    user_visible: bool
    resolution_required: bool


def build_assumption(
    *,
    assumption_id: str,
    key: str,
    value: str,
    reason: str,
    materiality: str,
    user_visible: bool,
    resolution_required: bool,
) -> Assumption:
    return Assumption(
        assumption_id=_require_nonempty_str(assumption_id, "assumptions[].assumption_id"),
        key=_require_nonempty_str(key, "assumptions[].key"),
        value=_require_str(value, "assumptions[].value"),
        reason=_require_nonempty_str(reason, "assumptions[].reason"),
        materiality=_require_member(materiality, MATERIALITY_VALUES, "assumptions[].materiality"),
        user_visible=_require_bool(user_visible, "assumptions[].user_visible"),
        resolution_required=_require_bool(resolution_required, "assumptions[].resolution_required"),
    )


# --- Output contract ----------------------------------------------------------


@dataclass(frozen=True)
class ContextBuilderOutput:
    contract_version: str
    request_id: str
    resolved_context: tuple[ResolvedContextItem, ...]
    missing_required_context: tuple[MissingContextItem, ...]
    missing_optional_context: tuple[MissingContextItem, ...]
    conflicts: tuple[ContextConflict, ...]
    assumptions: tuple[Assumption, ...]
    context_completeness: float
    answerability: str
    clarification_questions: tuple[str, ...]
    classification_basis: tuple[str, ...]


def build_output(
    *,
    request_id: str,
    answerability: str,
    context_completeness: float,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
    resolved_context: Sequence[ResolvedContextItem] = (),
    missing_required_context: Sequence[MissingContextItem] = (),
    missing_optional_context: Sequence[MissingContextItem] = (),
    conflicts: Sequence[ContextConflict] = (),
    assumptions: Sequence[Assumption] = (),
    clarification_questions: Sequence[str] = (),
    classification_basis: Sequence[str] = (),
) -> ContextBuilderOutput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise ContextBuilderError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}; got {contract_version!r}")
    validated_request_id = _require_nonempty_str(request_id, "request_id")
    validated_answerability = _require_member(answerability, ANSWERABILITY_VALUES, "answerability")
    validated_completeness = _require_bounded_float(context_completeness, "context_completeness")

    if validated_answerability == "CLARIFICATION_REQUIRED" and not clarification_questions:
        raise ContextBuilderError("clarification_questions is required when answerability is CLARIFICATION_REQUIRED")
    if validated_answerability != "CLARIFICATION_REQUIRED" and clarification_questions:
        raise ContextBuilderError(
            "clarification_questions must be empty unless answerability is CLARIFICATION_REQUIRED"
        )
    if len(clarification_questions) > 3:
        raise ContextBuilderError("clarification_questions must not exceed 3 items")

    validated_basis: list[str] = []
    for basis in classification_basis:
        validated_basis.append(_require_member(basis, CLASSIFICATION_BASIS_VALUES, "classification_basis[]"))

    return ContextBuilderOutput(
        contract_version=contract_version,
        request_id=validated_request_id,
        resolved_context=tuple(resolved_context),
        missing_required_context=tuple(missing_required_context),
        missing_optional_context=tuple(missing_optional_context),
        conflicts=tuple(conflicts),
        assumptions=tuple(assumptions),
        context_completeness=validated_completeness,
        answerability=validated_answerability,
        clarification_questions=tuple(clarification_questions),
        classification_basis=tuple(validated_basis),
    )
