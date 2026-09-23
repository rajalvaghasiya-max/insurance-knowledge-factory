"""Deterministic raw-phrase resolver for canonical insurance concepts (MO-024B).

This resolver consumes raw human terminology and the governed canonical concept
registry. It performs exact normalised matching only. It does not perform fuzzy
matching, semantic inference, evidence retrieval, product resolution,
applicability reasoning, comparison, ranking, or recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re

from insurance_intelligence.contracts.reasoning_plan import DOMAIN_VALUES
from insurance_intelligence.terminology.concept_registry import (
    CanonicalConceptDefinition,
    CanonicalConceptRegistry,
    CanonicalConceptRegistryError,
)
from insurance_intelligence.terminology.resolver import normalise_terminology_text


RESOLUTION_STATUSES = frozenset({"RESOLVED", "AMBIGUOUS", "NOT_RESOLVED", "INVALID_INPUT"})


@dataclass(frozen=True)
class CanonicalConceptResolution:
    resolution_id: str
    input_phrase: str
    normalised_phrase: str | None
    domain: str | None
    status: str
    selected_concept: CanonicalConceptDefinition | None
    candidates: tuple[CanonicalConceptDefinition, ...]
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in RESOLUTION_STATUSES:
            raise ValueError(f"unsupported resolution status: {self.status!r}")
        if self.status == "RESOLVED":
            if self.selected_concept is None or len(self.candidates) != 1:
                raise ValueError("RESOLVED requires exactly one selected candidate")
        else:
            if self.selected_concept is not None:
                raise ValueError(f"{self.status} cannot publish a selected concept")
        if self.status == "AMBIGUOUS" and len(self.candidates) < 2:
            raise ValueError("AMBIGUOUS requires at least two candidates")
        if self.status in {"NOT_RESOLVED", "INVALID_INPUT"} and self.candidates:
            raise ValueError(f"{self.status} cannot publish candidates")
        if not self.reason_codes:
            raise ValueError("reason_codes must not be empty")


def _stable_id(*parts: object) -> str:
    payload = "\x1f".join("" if part is None else str(part) for part in parts)
    return f"concept_resolution_{sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def _invalid(phrase: object, domain: object, reason: str) -> CanonicalConceptResolution:
    text = phrase if isinstance(phrase, str) else repr(phrase)
    return CanonicalConceptResolution(
        resolution_id=_stable_id("INVALID_INPUT", text, domain, reason),
        input_phrase=text,
        normalised_phrase=None,
        domain=domain if isinstance(domain, str) else None,
        status="INVALID_INPUT",
        selected_concept=None,
        candidates=(),
        reason_codes=(reason,),
    )


class CanonicalConceptResolver:
    """Resolve exact governed human terminology to one canonical concept."""

    def __init__(self, registry: CanonicalConceptRegistry) -> None:
        if not isinstance(registry, CanonicalConceptRegistry):
            raise TypeError("registry must be a CanonicalConceptRegistry")
        self._registry = registry

    def resolve(self, phrase: object, *, domain: object = None) -> CanonicalConceptResolution:
        if not isinstance(phrase, str) or not phrase.strip():
            return _invalid(phrase, domain, "INVALID_PHRASE")
        if domain is not None:
            if not isinstance(domain, str) or domain not in DOMAIN_VALUES:
                return _invalid(phrase, domain, "INVALID_DOMAIN")

        normalised = normalise_terminology_text(phrase)
        try:
            candidates = self._registry.candidates_for_phrase(phrase, domain=domain)
        except CanonicalConceptRegistryError:
            return _invalid(phrase, domain, "INVALID_REGISTRY_QUERY")

        if not candidates:
            return CanonicalConceptResolution(
                resolution_id=_stable_id("NOT_RESOLVED", normalised, domain),
                input_phrase=phrase,
                normalised_phrase=normalised,
                domain=domain,
                status="NOT_RESOLVED",
                selected_concept=None,
                candidates=(),
                reason_codes=("NO_EXACT_GOVERNED_CONCEPT_MATCH",),
            )

        if len(candidates) > 1:
            return CanonicalConceptResolution(
                resolution_id=_stable_id(
                    "AMBIGUOUS", normalised, domain, *(item.concept_id for item in candidates)
                ),
                input_phrase=phrase,
                normalised_phrase=normalised,
                domain=domain,
                status="AMBIGUOUS",
                selected_concept=None,
                candidates=candidates,
                reason_codes=("MULTIPLE_GOVERNED_CONCEPT_MATCHES",),
            )

        selected = candidates[0]
        return CanonicalConceptResolution(
            resolution_id=_stable_id("RESOLVED", normalised, domain, selected.concept_id),
            input_phrase=phrase,
            normalised_phrase=normalised,
            domain=domain,
            status="RESOLVED",
            selected_concept=selected,
            candidates=candidates,
            reason_codes=("EXACT_GOVERNED_CONCEPT_MATCH",),
        )


    def resolve_mentions(
        self,
        text: object,
        *,
        domain: object = None,
    ) -> tuple[CanonicalConceptResolution, ...]:
        """Resolve zero or more exact governed concept mentions inside one text.

        This is a bounded extension of exact phrase resolution. It scans only the
        language keys already present in the canonical registry, applies exact
        normalised word-boundary matching, skips ambiguous keys, and performs no
        fuzzy or semantic inference.
        """
        if not isinstance(text, str) or not text.strip():
            return ()
        if domain is not None and (
            not isinstance(domain, str) or domain not in DOMAIN_VALUES
        ):
            return ()

        normalised_text = normalise_terminology_text(text)
        matches: list[
            tuple[int, int, str, CanonicalConceptResolution]
        ] = []

        for definition in self._registry.all_concepts():
            if domain is not None and definition.domain != domain:
                continue
            for language_key in definition.language_keys():
                pattern = re.compile(
                    rf"(?<!\w){re.escape(language_key)}(?!\w)"
                )
                for match in pattern.finditer(normalised_text):
                    resolution = self.resolve(
                        language_key,
                        domain=definition.domain,
                    )
                    if (
                        resolution.status != "RESOLVED"
                        or resolution.selected_concept is None
                        or resolution.selected_concept.concept_id
                        != definition.concept_id
                    ):
                        continue
                    matches.append(
                        (
                            match.start(),
                            match.end(),
                            definition.concept_id,
                            resolution,
                        )
                    )

        matches.sort(
            key=lambda item: (
                item[0],
                -(item[1] - item[0]),
                item[2],
            )
        )

        selected: list[
            tuple[int, int, str, CanonicalConceptResolution]
        ] = []
        seen_concepts: set[str] = set()
        for candidate in matches:
            start, end, concept_id, _ = candidate
            if concept_id in seen_concepts:
                continue
            if any(
                start < selected_end and end > selected_start
                for selected_start, selected_end, _, _ in selected
            ):
                continue
            selected.append(candidate)
            seen_concepts.add(concept_id)

        selected.sort(key=lambda item: (item[0], item[2]))
        return tuple(item[3] for item in selected)
