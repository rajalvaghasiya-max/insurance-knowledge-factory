"""Deterministic raw-phrase resolver for canonical insurance concepts (MO-024B).

This resolver consumes raw human terminology and the governed canonical concept
registry. It performs exact normalised matching only. It does not perform fuzzy
matching, semantic inference, evidence retrieval, product resolution,
applicability reasoning, comparison, ranking, or recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

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
