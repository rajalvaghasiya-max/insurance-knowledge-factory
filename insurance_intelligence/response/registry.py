"""Deterministic response-format registry for MO-020B."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from insurance_intelligence.contracts.explanation import AUDIENCES
from insurance_intelligence.contracts.response import RESPONSE_FORMATS, RESPONSE_STATUSES, SECTION_TYPES

DIRECT_ANSWER_POLICIES = frozenset({"REQUIRED", "OPTIONAL", "FORBIDDEN"})
EVIDENCE_POLICIES = frozenset({"REQUIRED", "WHEN_AVAILABLE", "FORBIDDEN"})
LIMITATION_POLICIES = frozenset({"REQUIRED_WHEN_PRESENT", "ALWAYS", "FORBIDDEN"})
ASSUMPTION_POLICIES = frozenset({"WHEN_PRESENT", "ALWAYS", "FORBIDDEN"})
CLARIFICATION_POLICIES = frozenset({"REQUIRED", "FORBIDDEN"})


class ResponseRegistryError(ValueError):
    """Raised when response-format registry state is invalid."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResponseRegistryError(f"{label} must be a non-empty string")
    return value.strip()


def _member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise ResponseRegistryError(f"{label} must be one of {sorted(allowed)}; got {value!r}")
    return value  # type: ignore[return-value]


def _unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_text(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise ResponseRegistryError(f"{label} values must be unique")
    return result


@dataclass(frozen=True)
class ResponseFormatDefinition:
    format_id: str
    format_version: str
    response_format: str
    audiences: tuple[str, ...]
    response_statuses: tuple[str, ...]
    section_order: tuple[str, ...]
    allowed_section_types: tuple[str, ...]
    direct_answer_policy: str
    evidence_policy: str
    limitation_policy: str
    assumption_policy: str
    clarification_policy: str
    max_direct_answer_words: int
    max_section_words: int
    max_sections: int
    priority: int

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.format_id, self.format_version)


def build_format_definition(
    *,
    format_id: str,
    format_version: str,
    response_format: str,
    audiences: Sequence[str],
    response_statuses: Sequence[str],
    section_order: Sequence[str],
    allowed_section_types: Sequence[str],
    direct_answer_policy: str = "REQUIRED",
    evidence_policy: str = "WHEN_AVAILABLE",
    limitation_policy: str = "REQUIRED_WHEN_PRESENT",
    assumption_policy: str = "WHEN_PRESENT",
    clarification_policy: str = "FORBIDDEN",
    max_direct_answer_words: int = 80,
    max_section_words: int = 160,
    max_sections: int = 10,
    priority: int = 100,
) -> ResponseFormatDefinition:
    audience_values = _unique(audiences, "audiences")
    status_values = _unique(response_statuses, "response_statuses")
    order_values = _unique(section_order, "section_order")
    allowed_values = _unique(allowed_section_types, "allowed_section_types")
    if not audience_values or not status_values or not allowed_values:
        raise ResponseRegistryError("audiences, response_statuses, and allowed_section_types must not be empty")
    for audience in audience_values:
        _member(audience, AUDIENCES, "audiences[]")
    for status in status_values:
        _member(status, RESPONSE_STATUSES, "response_statuses[]")
    for section_type in allowed_values:
        _member(section_type, SECTION_TYPES, "allowed_section_types[]")
    for section_type in order_values:
        _member(section_type, SECTION_TYPES, "section_order[]")
    if not set(order_values) <= set(allowed_values):
        raise ResponseRegistryError("section_order must contain allowed section types only")
    for label, value in {
        "max_direct_answer_words": max_direct_answer_words,
        "max_section_words": max_section_words,
        "max_sections": max_sections,
    }.items():
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ResponseRegistryError(f"{label} must be a positive integer")
    if isinstance(priority, bool) or not isinstance(priority, int) or priority < 0:
        raise ResponseRegistryError("priority must be a non-negative integer")

    direct = _member(direct_answer_policy, DIRECT_ANSWER_POLICIES, "direct_answer_policy")
    evidence = _member(evidence_policy, EVIDENCE_POLICIES, "evidence_policy")
    limitation = _member(limitation_policy, LIMITATION_POLICIES, "limitation_policy")
    assumption = _member(assumption_policy, ASSUMPTION_POLICIES, "assumption_policy")
    clarification = _member(clarification_policy, CLARIFICATION_POLICIES, "clarification_policy")

    clarification_status = "CLARIFICATION_REQUIRED" in status_values
    answer_status = bool({"ANSWER", "ANSWER_WITH_LIMITATIONS"} & set(status_values))
    if clarification_status:
        if clarification != "REQUIRED":
            raise ResponseRegistryError("clarification formats must require clarification content")
        if direct != "FORBIDDEN" or evidence != "FORBIDDEN":
            raise ResponseRegistryError("clarification formats must forbid direct answers and evidence")
        if set(allowed_values) != {"CLARIFICATION"}:
            raise ResponseRegistryError("clarification formats may allow CLARIFICATION sections only")
    if answer_status:
        if clarification != "FORBIDDEN":
            raise ResponseRegistryError("answer formats must forbid clarification content")
        if direct == "FORBIDDEN":
            raise ResponseRegistryError("answer formats cannot forbid direct answers")
    if "ANSWER_WITH_LIMITATIONS" in status_values and limitation == "FORBIDDEN":
        raise ResponseRegistryError("answer-with-limitations formats cannot forbid limitations")

    return ResponseFormatDefinition(
        format_id=_text(format_id, "format_id"),
        format_version=_text(format_version, "format_version"),
        response_format=_member(response_format, RESPONSE_FORMATS, "response_format"),
        audiences=audience_values,
        response_statuses=status_values,
        section_order=order_values,
        allowed_section_types=allowed_values,
        direct_answer_policy=direct,
        evidence_policy=evidence,
        limitation_policy=limitation,
        assumption_policy=assumption,
        clarification_policy=clarification,
        max_direct_answer_words=max_direct_answer_words,
        max_section_words=max_section_words,
        max_sections=max_sections,
        priority=priority,
    )


class ResponseFormatRegistry:
    def __init__(self, definitions: Iterable[ResponseFormatDefinition] = ()) -> None:
        self._items: dict[tuple[str, str], ResponseFormatDefinition] = {}
        self._ids: set[str] = set()
        for definition in definitions:
            self.register(definition)

    def register(self, definition: ResponseFormatDefinition) -> None:
        if not isinstance(definition, ResponseFormatDefinition):
            raise ResponseRegistryError("definition must be a ResponseFormatDefinition")
        if definition.registry_key in self._items:
            raise ResponseRegistryError(
                f"duplicate response format registration: {definition.format_id}@{definition.format_version}"
            )
        if definition.format_id in self._ids:
            raise ResponseRegistryError(f"ambiguous duplicate format_id: {definition.format_id}")
        self._items[definition.registry_key] = definition
        self._ids.add(definition.format_id)

    def all_formats(self) -> tuple[ResponseFormatDefinition, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: (item.priority, item.format_id, item.format_version)))

    def eligible_formats(
        self,
        *,
        response_format: str,
        audience: str,
        response_status: str,
    ) -> tuple[ResponseFormatDefinition, ...]:
        _member(response_format, RESPONSE_FORMATS, "response_format")
        _member(audience, AUDIENCES, "audience")
        _member(response_status, RESPONSE_STATUSES, "response_status")
        return tuple(
            item
            for item in self.all_formats()
            if item.response_format == response_format
            and audience in item.audiences
            and response_status in item.response_statuses
        )

    def select_one(
        self,
        *,
        response_format: str,
        audience: str,
        response_status: str,
    ) -> ResponseFormatDefinition:
        eligible = self.eligible_formats(
            response_format=response_format,
            audience=audience,
            response_status=response_status,
        )
        if not eligible:
            raise ResponseRegistryError("no eligible response format definition")
        if len(eligible) > 1 and eligible[0].priority == eligible[1].priority:
            raise ResponseRegistryError("ambiguous eligible response format definitions")
        return eligible[0]
