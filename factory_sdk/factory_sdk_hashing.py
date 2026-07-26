"""
PolicyScna Factory SDK v1.0 — Deterministic Hashing

Stable JSON serialization and content hashing utilities.
These are central to Law 0: same input + same rules + same version = same output.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

from .factory_sdk_models import to_plain_data


_VOLATILE_KEYS = {
    "created_at",
    "manufactured_at",
    "started_at",
    "completed_at",
    "duration_ms",
    "processing_time_ms",
}


def canonicalize_for_hash(value: Any, *, remove_volatile_keys: bool = True) -> Any:
    """Return a deterministic representation suitable for hashing."""
    value = to_plain_data(value)

    if isinstance(value, dict):
        result: Dict[str, Any] = {}
        for key in sorted(value.keys()):
            if remove_volatile_keys and key in _VOLATILE_KEYS:
                continue
            result[str(key)] = canonicalize_for_hash(
                value[key], remove_volatile_keys=remove_volatile_keys
            )
        return result

    if isinstance(value, list):
        return [canonicalize_for_hash(v, remove_volatile_keys=remove_volatile_keys) for v in value]

    return value


def stable_json_dumps(value: Any, *, remove_volatile_keys: bool = False) -> str:
    canonical = canonicalize_for_hash(value, remove_volatile_keys=remove_volatile_keys)
    return json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(value: Any, *, prefix: str = "hash", remove_volatile_keys: bool = True, length: int = 24) -> str:
    payload = stable_json_dumps(value, remove_volatile_keys=remove_volatile_keys).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:length]
    return f"{prefix}_{digest}"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
