"""
PolicyScna Factory SDK v1.2 — Determinism Verifier

Compares two manufactured outputs after removing explicitly volatile fields.
This is the first step from deterministic_declared to deterministic_verified.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Set, Tuple

from ..factory_sdk_hashing import stable_hash
from ..factory_sdk_models import to_plain_data

DEFAULT_VOLATILE_KEYS: Set[str] = {
    "created_at",
    "manufactured_at",
    "duration_ms",
    "event_id",
}


def strip_volatile(value: Any, *, volatile_keys: Iterable[str] = DEFAULT_VOLATILE_KEYS) -> Any:
    keys = set(volatile_keys)
    value = to_plain_data(value)
    if isinstance(value, dict):
        return {k: strip_volatile(v, volatile_keys=keys) for k, v in value.items() if k not in keys}
    if isinstance(value, list):
        return [strip_volatile(v, volatile_keys=keys) for v in value]
    return value


def deterministic_fingerprint(value: Any, *, volatile_keys: Iterable[str] = DEFAULT_VOLATILE_KEYS) -> str:
    return stable_hash(strip_volatile(value, volatile_keys=volatile_keys), prefix="dfp")


def compare_deterministic_outputs(
    first: Dict[str, Any],
    second: Dict[str, Any],
    *,
    volatile_keys: Iterable[str] = DEFAULT_VOLATILE_KEYS,
) -> Tuple[bool, str, str]:
    first_hash = deterministic_fingerprint(first, volatile_keys=volatile_keys)
    second_hash = deterministic_fingerprint(second, volatile_keys=volatile_keys)
    return first_hash == second_hash, first_hash, second_hash
