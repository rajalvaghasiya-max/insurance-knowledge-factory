"""Canonical Context Builder output -> deterministic reasoning-context projection.

This bridge is intentionally narrow. It does not reread raw orchestration request
context, infer insurance facts, or reconstruct arbitrary Python objects from strings.
"""
from __future__ import annotations

from typing import Mapping

from insurance_intelligence.contracts.context import ContextBuilderOutput


class ReasoningContextProjectionError(ValueError):
    """Raised when canonical context cannot be projected safely."""


_TRUSTED_PROVENANCE = frozenset({"USER_PROVIDED", "DOCUMENT_RESOLVED", "SYSTEM_DERIVED"})
_BOOLEAN_KEYS = frozenset({"case_specific_applicability"})
_ENUM_VALUES: Mapping[str, frozenset[str]] = {
    "conditional_copayment_trigger_status": frozenset({"CONFIRMED", "NOT_TRIGGERED", "UNRESOLVED"}),
}


def _boolean(value: str, *, key: str) -> bool:
    normalized = value.strip().casefold()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ReasoningContextProjectionError(f"{key} must be canonical boolean text")


def _enum(value: str, *, key: str, allowed: frozenset[str]) -> str:
    normalized = value.strip().upper()
    if normalized not in allowed:
        raise ReasoningContextProjectionError(f"{key} must be one of {sorted(allowed)}")
    return normalized


def project_reasoning_context(context: ContextBuilderOutput) -> dict[str, object]:
    """Project trusted active canonical context into deterministic reasoning inputs.

    String values remain strings unless a key has an explicitly registered safe
    scalar coercion. No arbitrary mapping/list/object reconstruction is performed.
    """
    if not isinstance(context, ContextBuilderOutput):
        raise ReasoningContextProjectionError("context must be ContextBuilderOutput")

    projected: dict[str, object] = {}
    for item in context.resolved_context:
        if item.status != "ACTIVE" or item.provenance not in _TRUSTED_PROVENANCE:
            continue
        if item.key in projected:
            raise ReasoningContextProjectionError(f"duplicate active reasoning context key: {item.key}")

        if item.key in _BOOLEAN_KEYS:
            value: object = _boolean(item.value, key=item.key)
        elif item.key in _ENUM_VALUES:
            value = _enum(item.value, key=item.key, allowed=_ENUM_VALUES[item.key])
        else:
            value = item.value
        projected[item.key] = value

    return projected


__all__ = ["ReasoningContextProjectionError", "project_reasoning_context"]
