"""Generic immutable semantic attributes shared across governed boundaries."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


class SemanticAttributeContractError(ValueError):
    """Raised when a governed semantic attribute is invalid."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SemanticAttributeContractError(f"{label} must be a non-empty string")
    return value.strip()


def _unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_text(value, f"{label}[]") for value in values)
    if not result:
        raise SemanticAttributeContractError(f"{label} must not be empty")
    if len(result) != len(set(result)):
        raise SemanticAttributeContractError(f"{label} values must be unique")
    return result


@dataclass(frozen=True)
class GovernedSemanticAttribute:
    key: str
    value: str
    evidence_references: tuple[str, ...]


def build_governed_semantic_attribute(
    *, key: str, value: str, evidence_references: Sequence[str]
) -> GovernedSemanticAttribute:
    return GovernedSemanticAttribute(
        key=_text(key, "key"),
        value=_text(value, "value"),
        evidence_references=_unique(evidence_references, "evidence_references"),
    )


def validate_semantic_attributes(
    values: Sequence[GovernedSemanticAttribute],
) -> tuple[GovernedSemanticAttribute, ...]:
    attributes = tuple(values)
    if not all(isinstance(item, GovernedSemanticAttribute) for item in attributes):
        raise SemanticAttributeContractError(
            "semantic_attributes must contain GovernedSemanticAttribute values"
        )
    keys = [item.key for item in attributes]
    if len(keys) != len(set(keys)):
        raise SemanticAttributeContractError("semantic attribute keys must be unique")
    return attributes


__all__ = [
    "GovernedSemanticAttribute",
    "SemanticAttributeContractError",
    "build_governed_semantic_attribute",
    "validate_semantic_attributes",
]
