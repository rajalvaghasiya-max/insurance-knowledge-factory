"""
life_intelligence_lab.calculators.canonical
=============================================

Deterministic canonical serialization and SHA-256 hashing for
normalized request inputs and calculation outputs.

Determinism contract: given the same (calculator_id, calculator_version,
calculation_date, currency, method, normalized_inputs), `hash_input`
always returns the same hash -- regardless of when, how many times, or
on which run it is called. The same holds for `hash_output` given the
same output values. Nothing in this module reads the clock, generates a
random value, or depends on platform-specific float formatting (all
values are hashed as their canonical Decimal-derived strings).

This module is self-contained and does NOT import anything from the
sibling LIFE-PROTOTYPE-001 AMFI adapter code, even though it follows the
same general pattern (fixed field order, compact JSON, sha256) -- see
ARCHITECTURE.md for why the pattern is reused but the code is not.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional


def _dumps_compact(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_input(
    calculator_id: str,
    calculator_version: int,
    calculation_date: str,
    currency: Optional[str],
    method: Optional[str],
    normalized_inputs: Dict[str, str],
    extra_content: Optional[dict] = None,
) -> str:
    """
    Hash of exactly the content that determines a calculation's outcome:
    which calculator+version, what date context, what currency/method,
    and the fully normalized (decimal-safe-string) input values -- with
    input field names sorted so key order never depends on iteration order.

    `extra_content` is new in LIFE-PROTOTYPE-003, used only by dated
    cash-flow calculators to fold the normalized cash-flow list into the
    input hash (two different cash-flow lists MUST hash differently).
    It is included in the payload ONLY when not `None`, so every
    pre-existing Prototype 002 calculator (which never passes it)
    produces the byte-identical hash payload -- and therefore the
    byte-identical hash value -- it always has.
    """
    payload = {
        "calculator_id": calculator_id,
        "calculator_version": calculator_version,
        "calculation_date": calculation_date,
        "currency": currency,
        "method": method,
        "normalized_inputs": dict(sorted(normalized_inputs.items())),
    }
    if extra_content is not None:
        payload["extra_content"] = extra_content
    return sha256_hex(_dumps_compact(payload))


def hash_output(output_after_rounding: Dict[str, str], output_units: Dict[str, str]) -> str:
    payload = {
        "output_after_rounding": dict(sorted(output_after_rounding.items())),
        "output_units": dict(sorted(output_units.items())),
    }
    return sha256_hex(_dumps_compact(payload))


def derive_trace_id(input_hash: str, output_hash: str) -> str:
    """Deterministic, content-derived trace id -- never a random UUID."""
    return f"trace_{input_hash[:16]}_{output_hash[:16]}"


def derive_result_id_success(input_hash: str, output_hash: str) -> str:
    return f"result_{input_hash[:16]}_{output_hash[:16]}"


def derive_result_id_failed_closed(input_hash: str) -> str:
    return f"result_failed_{input_hash[:24]}"


def derive_result_id_unresolvable(request_id: str, calculator_id: str, calculator_version: int, envelope_reason: str) -> str:
    """
    Used when a result is produced before normalized inputs exist at all
    (unknown/retired calculator, or a malformed request envelope) -- there
    is no normalized-input hash to derive from, so the id is instead
    derived from the caller-supplied request_id and the calculator
    reference, which is still fully deterministic (no randomness), just
    not tied to input content that was never successfully normalized.
    """
    basis = sha256_hex(_dumps_compact({
        "request_id": request_id,
        "calculator_id": calculator_id,
        "calculator_version": calculator_version,
        "envelope_reason": envelope_reason,
    }))
    return f"result_unresolvable_{basis[:16]}"


def dumps_trace_canonical(trace_dict: dict, field_order: List[str]) -> str:
    ordered = {field: trace_dict[field] for field in field_order}
    return _dumps_compact(ordered)


def dumps_result_canonical(result_dict: dict, field_order: List[str]) -> str:
    ordered = {field: result_dict[field] for field in field_order}
    return _dumps_compact(ordered)


def hash_trace_content(trace_dict: dict, field_order: List[str]) -> str:
    """A single hash over the ENTIRE canonical trace record -- used to
    prove full trace reproducibility across repeated runs / replay,
    distinct from the narrower `input_hash`/`output_hash` embedded within
    the trace itself."""
    return sha256_hex(dumps_trace_canonical(trace_dict, field_order))


def hash_result_content(result_dict: dict, field_order: List[str]) -> str:
    return sha256_hex(dumps_result_canonical(result_dict, field_order))
