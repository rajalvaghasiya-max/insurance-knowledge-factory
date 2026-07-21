"""Deterministic style and terminology registries for MO-019B."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from insurance_intelligence.contracts.explanation import AUDIENCES, EXPLANATION_MODES, READING_LEVELS

STYLE_TONES = frozenset({"NEUTRAL", "REASSURING", "ADVISORY", "TECHNICAL"})
SENTENCE_LENGTHS = frozenset({"SHORT", "MEDIUM", "LONG"})
BULLET_POLICIES = frozenset({"NEVER", "WHEN_HELPFUL", "PREFERRED"})
TERMINOLOGY_SCOPES = frozenset({"GLOBAL", "HEALTH", "MOTOR", "LIFE", "TRAVEL"})
TERMINOLOGY_ACTIONS = frozenset({"PRESERVE", "SIMPLIFY", "EXPAND", "DEFINE"})


class ExplanationRegistryError(ValueError):
    """Raised when explanation style or terminology registry state is invalid."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExplanationRegistryError(f"{label} must be a non-empty string")
    return value.strip()


def _member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise ExplanationRegistryError(f"{label} must be one of {sorted(allowed)}; got {value!r}")
    return value  # type: ignore[return-value]


def _unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_text(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise ExplanationRegistryError(f"{label} values must be unique")
    return result


@dataclass(frozen=True)
class ExplanationStyleDefinition:
    style_id: str
    style_version: str
    audience: str
    reading_level: str
    explanation_modes: tuple[str, ...]
    tone: str
    sentence_length: str
    bullet_policy: str
    preserve_conditions: bool
    preserve_limitations: bool
    preserve_evidence_notes: bool
    max_section_words: int
    priority: int

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.style_id, self.style_version)


def build_style_definition(
    *,
    style_id: str,
    style_version: str,
    audience: str,
    reading_level: str,
    explanation_modes: Sequence[str],
    tone: str = "NEUTRAL",
    sentence_length: str = "SHORT",
    bullet_policy: str = "WHEN_HELPFUL",
    preserve_conditions: bool = True,
    preserve_limitations: bool = True,
    preserve_evidence_notes: bool = True,
    max_section_words: int = 120,
    priority: int = 100,
) -> ExplanationStyleDefinition:
    for label, value in {
        "preserve_conditions": preserve_conditions,
        "preserve_limitations": preserve_limitations,
        "preserve_evidence_notes": preserve_evidence_notes,
    }.items():
        if not isinstance(value, bool):
            raise ExplanationRegistryError(f"{label} must be boolean")
    if isinstance(max_section_words, bool) or not isinstance(max_section_words, int) or max_section_words <= 0:
        raise ExplanationRegistryError("max_section_words must be a positive integer")
    if isinstance(priority, bool) or not isinstance(priority, int) or priority < 0:
        raise ExplanationRegistryError("priority must be a non-negative integer")
    modes = _unique(explanation_modes, "explanation_modes")
    if not modes:
        raise ExplanationRegistryError("explanation_modes must not be empty")
    for mode in modes:
        _member(mode, EXPLANATION_MODES, "explanation_modes[]")
    if not preserve_conditions or not preserve_limitations:
        raise ExplanationRegistryError("styles must preserve conditions and limitations")
    return ExplanationStyleDefinition(
        style_id=_text(style_id, "style_id"),
        style_version=_text(style_version, "style_version"),
        audience=_member(audience, AUDIENCES, "audience"),
        reading_level=_member(reading_level, READING_LEVELS, "reading_level"),
        explanation_modes=modes,
        tone=_member(tone, STYLE_TONES, "tone"),
        sentence_length=_member(sentence_length, SENTENCE_LENGTHS, "sentence_length"),
        bullet_policy=_member(bullet_policy, BULLET_POLICIES, "bullet_policy"),
        preserve_conditions=preserve_conditions,
        preserve_limitations=preserve_limitations,
        preserve_evidence_notes=preserve_evidence_notes,
        max_section_words=max_section_words,
        priority=priority,
    )


@dataclass(frozen=True)
class TerminologyDefinition:
    terminology_id: str
    terminology_version: str
    source_term: str
    rendered_term: str
    action: str
    audience: str
    reading_levels: tuple[str, ...]
    explanation_modes: tuple[str, ...]
    scope: str
    meaning_preserved: bool
    definition_text: str
    priority: int

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.terminology_id, self.terminology_version)


def build_terminology_definition(
    *,
    terminology_id: str,
    terminology_version: str,
    source_term: str,
    rendered_term: str,
    action: str,
    audience: str,
    reading_levels: Sequence[str],
    explanation_modes: Sequence[str],
    scope: str = "GLOBAL",
    meaning_preserved: bool = True,
    definition_text: str = "",
    priority: int = 100,
) -> TerminologyDefinition:
    if not isinstance(meaning_preserved, bool):
        raise ExplanationRegistryError("meaning_preserved must be boolean")
    if not meaning_preserved:
        raise ExplanationRegistryError("registered terminology must preserve meaning")
    if isinstance(priority, bool) or not isinstance(priority, int) or priority < 0:
        raise ExplanationRegistryError("priority must be a non-negative integer")
    levels = _unique(reading_levels, "reading_levels")
    modes = _unique(explanation_modes, "explanation_modes")
    if not levels or not modes:
        raise ExplanationRegistryError("reading_levels and explanation_modes must not be empty")
    for level in levels:
        _member(level, READING_LEVELS, "reading_levels[]")
    for mode in modes:
        _member(mode, EXPLANATION_MODES, "explanation_modes[]")
    action_value = _member(action, TERMINOLOGY_ACTIONS, "action")
    definition = definition_text.strip() if isinstance(definition_text, str) else ""
    if action_value in {"DEFINE", "EXPAND"} and not definition:
        raise ExplanationRegistryError("DEFINE and EXPAND terminology require definition_text")
    return TerminologyDefinition(
        terminology_id=_text(terminology_id, "terminology_id"),
        terminology_version=_text(terminology_version, "terminology_version"),
        source_term=_text(source_term, "source_term"),
        rendered_term=_text(rendered_term, "rendered_term"),
        action=action_value,
        audience=_member(audience, AUDIENCES, "audience"),
        reading_levels=levels,
        explanation_modes=modes,
        scope=_member(scope, TERMINOLOGY_SCOPES, "scope"),
        meaning_preserved=meaning_preserved,
        definition_text=definition,
        priority=priority,
    )


class ExplanationStyleRegistry:
    def __init__(self, styles: Iterable[ExplanationStyleDefinition] = ()) -> None:
        self._items: dict[tuple[str, str], ExplanationStyleDefinition] = {}
        self._ids: set[str] = set()
        for item in styles:
            self.register(item)

    def register(self, item: ExplanationStyleDefinition) -> None:
        if not isinstance(item, ExplanationStyleDefinition):
            raise ExplanationRegistryError("style must be an ExplanationStyleDefinition")
        if item.registry_key in self._items:
            raise ExplanationRegistryError(f"duplicate style registration: {item.style_id}@{item.style_version}")
        if item.style_id in self._ids:
            raise ExplanationRegistryError(f"ambiguous duplicate style_id: {item.style_id}")
        self._items[item.registry_key] = item
        self._ids.add(item.style_id)

    def all_styles(self) -> tuple[ExplanationStyleDefinition, ...]:
        return tuple(sorted(self._items.values(), key=lambda x: (x.priority, x.style_id, x.style_version)))

    def eligible_styles(self, *, audience: str, reading_level: str, explanation_mode: str) -> tuple[ExplanationStyleDefinition, ...]:
        _member(audience, AUDIENCES, "audience")
        _member(reading_level, READING_LEVELS, "reading_level")
        _member(explanation_mode, EXPLANATION_MODES, "explanation_mode")
        return tuple(
            item for item in self.all_styles()
            if item.audience == audience and item.reading_level == reading_level and explanation_mode in item.explanation_modes
        )


class TerminologyRegistry:
    def __init__(self, items: Iterable[TerminologyDefinition] = ()) -> None:
        self._items: dict[tuple[str, str], TerminologyDefinition] = {}
        self._ids: set[str] = set()
        for item in items:
            self.register(item)

    def register(self, item: TerminologyDefinition) -> None:
        if not isinstance(item, TerminologyDefinition):
            raise ExplanationRegistryError("terminology must be a TerminologyDefinition")
        if item.registry_key in self._items:
            raise ExplanationRegistryError(
                f"duplicate terminology registration: {item.terminology_id}@{item.terminology_version}"
            )
        if item.terminology_id in self._ids:
            raise ExplanationRegistryError(f"ambiguous duplicate terminology_id: {item.terminology_id}")
        self._items[item.registry_key] = item
        self._ids.add(item.terminology_id)

    def all_terms(self) -> tuple[TerminologyDefinition, ...]:
        return tuple(sorted(self._items.values(), key=lambda x: (x.priority, x.terminology_id, x.terminology_version)))

    def eligible_terms(
        self,
        *,
        source_terms: Sequence[str],
        audience: str,
        reading_level: str,
        explanation_mode: str,
        scope: str = "GLOBAL",
    ) -> tuple[TerminologyDefinition, ...]:
        terms = set(_unique(source_terms, "source_terms"))
        _member(audience, AUDIENCES, "audience")
        _member(reading_level, READING_LEVELS, "reading_level")
        _member(explanation_mode, EXPLANATION_MODES, "explanation_mode")
        _member(scope, TERMINOLOGY_SCOPES, "scope")
        return tuple(
            item for item in self.all_terms()
            if item.source_term in terms
            and item.audience == audience
            and reading_level in item.reading_levels
            and explanation_mode in item.explanation_modes
            and item.scope in {"GLOBAL", scope}
        )
