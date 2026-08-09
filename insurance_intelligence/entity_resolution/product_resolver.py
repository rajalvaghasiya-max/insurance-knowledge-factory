"""Deterministic governed product entity resolution for ER-1.

This runtime layer consumes already-governed product identity records. It does
not verify source documents, extract UINs, resolve insurance terminology,
retrieve product evidence, or infer product suitability. Factory-side identity
verification remains owned by the existing product identity pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Sequence

from insurance_intelligence.terminology.resolver import normalise_terminology_text

ENTITY_RESOLUTION_STATUSES = frozenset(
    {"RESOLVED", "AMBIGUOUS", "NOT_RESOLVED", "INVALID_INPUT"}
)
ENTITY_MATCH_METHODS = frozenset(
    {"CANONICAL_ENTITY_ID", "UIN", "GOVERNED_ALIAS", "CANONICAL_PRODUCT_NAME"}
)


class ProductEntityRegistryError(ValueError):
    """Raised when governed product entity registry state is invalid."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProductEntityRegistryError(f"{label} must be a non-empty string")
    return value.strip()


def _unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ProductEntityRegistryError(f"{label} must be a sequence of strings")
    result = tuple(_text(value, f"{label}[]") for value in values)
    keys = tuple(normalise_terminology_text(value) for value in result)
    if len(keys) != len(set(keys)):
        raise ProductEntityRegistryError(f"{label} contains duplicate normalised values")
    return result


def _normalise_uin(value: str) -> str:
    return "".join(value.upper().split())


@dataclass(frozen=True)
class GovernedProductEntity:
    canonical_entity_id: str
    insurer_id: str
    product_id: str
    canonical_product_name: str
    uin: str | None = None
    aliases: tuple[str, ...] = ()
    product_variants: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        entity_id = _text(self.canonical_entity_id, "canonical_entity_id")
        insurer_id = _text(self.insurer_id, "insurer_id")
        product_id = _text(self.product_id, "product_id")
        canonical_name = _text(self.canonical_product_name, "canonical_product_name")
        if entity_id != f"{insurer_id}:{product_id}":
            raise ProductEntityRegistryError(
                "canonical_entity_id must equal insurer_id:product_id"
            )
        object.__setattr__(self, "canonical_entity_id", entity_id)
        object.__setattr__(self, "insurer_id", insurer_id)
        object.__setattr__(self, "product_id", product_id)
        object.__setattr__(self, "canonical_product_name", canonical_name)
        if self.uin is not None:
            uin = _normalise_uin(_text(self.uin, "uin"))
            if len(uin) < 8:
                raise ProductEntityRegistryError("uin must be a compact UIN-like identifier")
            object.__setattr__(self, "uin", uin)
        object.__setattr__(self, "aliases", _unique(self.aliases, "aliases"))
        object.__setattr__(
            self, "product_variants", _unique(self.product_variants, "product_variants")
        )


class GovernedProductEntityRegistry:
    """Immutable-by-interface registry for already-governed product identities."""

    def __init__(self, entities: Iterable[GovernedProductEntity] = ()) -> None:
        values = tuple(entities)
        if any(not isinstance(item, GovernedProductEntity) for item in values):
            raise ProductEntityRegistryError(
                "entities must contain GovernedProductEntity values"
            )
        self._entities: dict[str, GovernedProductEntity] = {}
        for entity in values:
            if entity.canonical_entity_id in self._entities:
                raise ProductEntityRegistryError(
                    f"duplicate canonical_entity_id: {entity.canonical_entity_id}"
                )
            self._entities[entity.canonical_entity_id] = entity

    def all_entities(self) -> tuple[GovernedProductEntity, ...]:
        return tuple(self._entities[key] for key in sorted(self._entities))

    def get(self, canonical_entity_id: str) -> GovernedProductEntity:
        key = _text(canonical_entity_id, "canonical_entity_id")
        try:
            return self._entities[key]
        except KeyError as exc:
            raise ProductEntityRegistryError(
                f"canonical_entity_id not registered: {key}"
            ) from exc


@dataclass(frozen=True)
class ProductEntityResolution:
    resolution_id: str
    input_value: str
    status: str
    selected_entity: GovernedProductEntity | None
    candidates: tuple[GovernedProductEntity, ...]
    match_method: str | None
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in ENTITY_RESOLUTION_STATUSES:
            raise ValueError(f"unsupported entity resolution status: {self.status!r}")
        if not self.reason_codes:
            raise ValueError("reason_codes must not be empty")
        if self.status == "RESOLVED":
            if self.selected_entity is None or len(self.candidates) != 1:
                raise ValueError("RESOLVED requires exactly one selected entity")
            if self.match_method not in ENTITY_MATCH_METHODS:
                raise ValueError("RESOLVED requires a supported match_method")
        else:
            if self.selected_entity is not None or self.match_method is not None:
                raise ValueError(f"{self.status} cannot publish a selected entity")
        if self.status == "AMBIGUOUS" and len(self.candidates) < 2:
            raise ValueError("AMBIGUOUS requires at least two candidates")
        if self.status in {"NOT_RESOLVED", "INVALID_INPUT"} and self.candidates:
            raise ValueError(f"{self.status} cannot publish candidates")


def _stable_id(*parts: object) -> str:
    payload = "\x1f".join("" if part is None else str(part) for part in parts)
    return f"entity_resolution_{sha256(payload.encode('utf-8')).hexdigest()[:24]}"


class ProductEntityResolver:
    """Resolve product identity by deterministic governed precedence only."""

    def __init__(self, registry: GovernedProductEntityRegistry) -> None:
        if not isinstance(registry, GovernedProductEntityRegistry):
            raise TypeError("registry must be a GovernedProductEntityRegistry")
        self._registry = registry

    def resolve(self, value: object) -> ProductEntityResolution:
        if not isinstance(value, str) or not value.strip():
            text = value if isinstance(value, str) else repr(value)
            return ProductEntityResolution(
                resolution_id=_stable_id("INVALID_INPUT", text),
                input_value=text,
                status="INVALID_INPUT",
                selected_entity=None,
                candidates=(),
                match_method=None,
                reason_codes=("INVALID_PRODUCT_REFERENCE",),
            )

        raw = value.strip()
        entities = self._registry.all_entities()

        exact_id = tuple(item for item in entities if item.canonical_entity_id == raw)
        if exact_id:
            return self._from_candidates(raw, exact_id, "CANONICAL_ENTITY_ID")

        uin_key = _normalise_uin(raw)
        uin_matches = tuple(item for item in entities if item.uin == uin_key)
        if uin_matches:
            return self._from_candidates(raw, uin_matches, "UIN")

        language_key = normalise_terminology_text(raw)
        alias_matches = tuple(
            item
            for item in entities
            if language_key
            in {normalise_terminology_text(alias) for alias in item.aliases}
        )
        if alias_matches:
            return self._from_candidates(raw, alias_matches, "GOVERNED_ALIAS")

        canonical_name_matches = tuple(
            item
            for item in entities
            if normalise_terminology_text(item.canonical_product_name) == language_key
        )
        if canonical_name_matches:
            return self._from_candidates(
                raw, canonical_name_matches, "CANONICAL_PRODUCT_NAME"
            )

        return ProductEntityResolution(
            resolution_id=_stable_id("NOT_RESOLVED", language_key),
            input_value=raw,
            status="NOT_RESOLVED",
            selected_entity=None,
            candidates=(),
            match_method=None,
            reason_codes=("NO_GOVERNED_PRODUCT_MATCH",),
        )

    @staticmethod
    def _from_candidates(
        raw: str,
        candidates: tuple[GovernedProductEntity, ...],
        method: str,
    ) -> ProductEntityResolution:
        ordered = tuple(sorted(candidates, key=lambda item: item.canonical_entity_id))
        if len(ordered) > 1:
            return ProductEntityResolution(
                resolution_id=_stable_id(
                    "AMBIGUOUS", method, raw, *(item.canonical_entity_id for item in ordered)
                ),
                input_value=raw,
                status="AMBIGUOUS",
                selected_entity=None,
                candidates=ordered,
                match_method=None,
                reason_codes=(f"MULTIPLE_{method}_MATCHES",),
            )
        selected = ordered[0]
        return ProductEntityResolution(
            resolution_id=_stable_id(
                "RESOLVED", method, raw, selected.canonical_entity_id
            ),
            input_value=raw,
            status="RESOLVED",
            selected_entity=selected,
            candidates=ordered,
            match_method=method,
            reason_codes=(f"EXACT_{method}_MATCH",),
        )
