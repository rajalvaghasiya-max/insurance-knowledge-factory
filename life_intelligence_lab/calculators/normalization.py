"""
life_intelligence_lab.calculators.normalization
=================================================

Normalizes a CalculationRequest's raw input_values/input_units into
canonical, decimal-safe internal representations, driven entirely by the
target CalculatorDefinition's `required_input_schema`.

Nothing here guesses, clamps, or repairs a value. Every rejection raises
a `NormalizationError` carrying a short, stable, machine-readable reason
code (used verbatim as CalculationResult.reason for INVALID_INPUT).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

from life_intelligence_lab.calculators.contracts import (
    CalculatorDefinition,
    FIELD_KIND_COUNT,
    FIELD_KIND_DECIMAL,
    FIELD_KIND_DECIMAL_LIST,
    FIELD_KIND_FLAG,
    FIELD_KIND_MONEY,
    FIELD_KIND_RATE,
    FIELD_KIND_STRING,
    NormalizedInput,
)

SUPPORTED_RATE_UNITS = ("decimal", "percentage")
SUPPORTED_CURRENCIES = ("INR", "USD", "GBP", "EUR")


class NormalizationError(Exception):
    """Raised with a short, stable reason code as the message."""


def to_decimal_safe(raw: object, field_name: str) -> Decimal:
    """
    Public wrapper around the decimal-safe parser below, exposed
    specifically for reuse by `calculators/cash_flow.py` (Prototype 003)
    -- this is the "reuse the existing calculator framework... normalisation"
    requirement satisfied by exposing one function rather than
    duplicating float/NaN/Infinity/bool rejection logic in a second
    module.
    """
    return _to_decimal_safe(raw, field_name)


def _to_decimal_safe(raw: object, field_name: str) -> Decimal:
    """
    Converts a raw JSON-loaded value to Decimal without ever passing
    through a Python float, to guarantee no binary-floating-point
    precision loss enters the pipeline. Strings and ints are accepted;
    float is explicitly rejected (the caller must quote it as a string
    in the request), and bool is rejected (Python's bool is a subclass
    of int and would otherwise silently coerce to 0/1).
    """
    if isinstance(raw, bool):
        raise NormalizationError(f"malformed_decimal_value:{field_name}: boolean not accepted as a numeric value")
    if isinstance(raw, float):
        raise NormalizationError(
            f"malformed_decimal_value:{field_name}: float type not accepted directly "
            f"(precision cannot be guaranteed) -- provide as a quoted decimal string"
        )
    if isinstance(raw, int):
        return Decimal(raw)
    if isinstance(raw, str):
        value = raw.strip()
        if not value:
            raise NormalizationError(f"missing_required_input:{field_name}")
        try:
            decimal_value = Decimal(value)
        except InvalidOperation:
            raise NormalizationError(f"malformed_decimal_value:{field_name}") from None
        if not decimal_value.is_finite():
            raise NormalizationError(f"non_finite_value:{field_name}")
        return decimal_value
    raise NormalizationError(f"malformed_decimal_value:{field_name}: unsupported input type")


def _normalize_rate_field(
    field_name: str, raw_value: object, unit: Optional[str]
) -> Tuple[Decimal, str, str]:
    if unit is None:
        raise NormalizationError(f"ambiguous_rate_unit:{field_name}: no unit specified (decimal|percentage required)")
    if unit not in SUPPORTED_RATE_UNITS:
        raise NormalizationError(f"invalid_unit:{field_name}:{unit}")
    decimal_value = _to_decimal_safe(raw_value, field_name)
    if unit == "percentage":
        normalized = decimal_value / Decimal(100)
    else:
        normalized = decimal_value
    if not normalized.is_finite():
        raise NormalizationError(f"non_finite_value:{field_name}")
    return normalized, unit, "decimal_fraction"


def _normalize_count_field(field_name: str, raw_value: object, schema_entry: dict) -> Decimal:
    decimal_value = _to_decimal_safe(raw_value, field_name)
    if decimal_value != decimal_value.to_integral_value():
        raise NormalizationError(f"invalid_unit:{field_name}: periods must be a whole number")
    if decimal_value < 0:
        raise NormalizationError(f"negative_period_count:{field_name}")
    min_value = schema_entry.get("min")
    if min_value is not None and decimal_value < min_value:
        raise NormalizationError(f"below_minimum:{field_name}: minimum is {min_value}")
    return decimal_value


def _normalize_string_field(field_name: str, raw_value: object, schema_entry: dict) -> str:
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise NormalizationError(f"missing_required_input:{field_name}")
    value = raw_value.strip().upper()
    allowed = schema_entry.get("allowed_values")
    if allowed is not None and value not in allowed:
        # Use a reason code appropriate to what this field actually is, not a
        # currency-specific one hardcoded for every whitelisted string field
        # (day_count_convention, duplicate_date_policy, etc. are NOT currencies).
        reason_prefix = schema_entry.get("unsupported_value_reason", "unsupported_value")
        raise NormalizationError(f"{reason_prefix}:{field_name}:{raw_value}")
    return value


def _normalize_flag_field(field_name: str, raw_value: object) -> bool:
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str) and raw_value.strip().lower() in ("true", "false"):
        return raw_value.strip().lower() == "true"
    raise NormalizationError(f"invalid_unit:{field_name}: expected a boolean flag")


def normalize_request_inputs(
    calc_def: CalculatorDefinition,
    input_values: Dict[str, object],
    input_units: Dict[str, str],
) -> List[NormalizedInput]:
    """
    Returns a list of NormalizedInput records, one per field declared in
    the calculator's required_input_schema, in schema declaration order
    (which is itself fixed per calculator, giving deterministic ordering
    downstream). Raises NormalizationError on the first violation found,
    scanning fields in schema order for a deterministic, reproducible
    failure reason across repeated runs against the same bad input.
    """
    normalized: List[NormalizedInput] = []

    for field_name, schema_entry in calc_def.required_input_schema.items():
        kind = schema_entry["kind"]
        required = schema_entry.get("required", True)
        present = field_name in input_values and input_values[field_name] is not None

        if not present:
            if required:
                raise NormalizationError(f"missing_required_input:{field_name}")
            default = schema_entry.get("default")
            if default is None:
                continue
            input_values = dict(input_values)
            input_values[field_name] = default

        raw_value = input_values[field_name]
        unit = input_units.get(field_name)

        if kind == FIELD_KIND_RATE:
            normalized_decimal, resolved_unit, normalized_unit = _normalize_rate_field(field_name, raw_value, unit)
            normalized.append(NormalizedInput(
                field_name=field_name,
                original_value=str(raw_value),
                original_unit=resolved_unit,
                normalized_value=str(normalized_decimal),
                normalized_unit=normalized_unit,
            ))

        elif kind in (FIELD_KIND_MONEY, FIELD_KIND_DECIMAL):
            decimal_value = _to_decimal_safe(raw_value, field_name)
            if kind == FIELD_KIND_MONEY and not schema_entry.get("allow_negative", False) and decimal_value < 0:
                raise NormalizationError(f"negative_amount_not_supported:{field_name}")
            normalized.append(NormalizedInput(
                field_name=field_name,
                original_value=str(raw_value),
                original_unit=unit,
                normalized_value=str(decimal_value),
                normalized_unit="decimal",
            ))

        elif kind == FIELD_KIND_COUNT:
            decimal_value = _normalize_count_field(field_name, raw_value, schema_entry)
            normalized.append(NormalizedInput(
                field_name=field_name,
                original_value=str(raw_value),
                original_unit=unit,
                normalized_value=str(decimal_value.to_integral_value()),
                normalized_unit="periods",
            ))

        elif kind == FIELD_KIND_DECIMAL_LIST:
            decimal_list = _normalize_decimal_list_field(field_name, raw_value)
            import json as _json
            normalized.append(NormalizedInput(
                field_name=field_name,
                original_value=str(raw_value),
                original_unit=unit,
                normalized_value=_json.dumps([str(d) for d in decimal_list]),
                normalized_unit="decimal_list",
            ))

        elif kind == FIELD_KIND_STRING:
            value = _normalize_string_field(field_name, raw_value, schema_entry)
            normalized.append(NormalizedInput(
                field_name=field_name,
                original_value=str(raw_value),
                original_unit=None,
                normalized_value=value,
                normalized_unit="code",
            ))

        elif kind == FIELD_KIND_FLAG:
            value = _normalize_flag_field(field_name, raw_value)
            normalized.append(NormalizedInput(
                field_name=field_name,
                original_value=str(raw_value),
                original_unit=None,
                normalized_value="true" if value else "false",
                normalized_unit="boolean",
            ))
        else:
            raise NormalizationError(f"malformed_decimal_value:{field_name}: unknown field kind '{kind}'")

    return normalized


def validate_iso_date(raw: object, field_name: str) -> str:
    """
    Strict ISO-8601 (YYYY-MM-DD) date validator, exposed for reuse by
    `calculators/cash_flow.py`. Deliberately stricter than Prototype
    001's AMFI DD-Mon-YYYY parser -- this cash-flow contract requires
    callers to supply already-ISO dates rather than attempting to guess
    among multiple input formats, keeping normalization unambiguous.
    """
    if not isinstance(raw, str):
        raise NormalizationError(f"invalid_date_format:{field_name}: expected an ISO-8601 date string")
    value = raw.strip()
    import re as _re
    from datetime import date as _date

    if not _re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        raise NormalizationError(f"invalid_date_format:{field_name}: '{raw}' is not YYYY-MM-DD")
    try:
        parsed = _date.fromisoformat(value)
    except ValueError:
        raise NormalizationError(f"invalid_date_format:{field_name}: '{raw}' is not a real calendar date") from None
    return parsed.isoformat()


def validate_currency(currency: Optional[str]) -> str:
    """
    Validates the top-level CalculationRequest.currency field. Currency
    is a request-envelope concept (not a per-field input in
    required_input_schema), so it is validated once here rather than
    duplicated as a schema field on every money-producing calculator.
    """
    if currency is None or not isinstance(currency, str) or not currency.strip():
        raise NormalizationError("missing_required_input:currency")
    value = currency.strip().upper()
    if value not in SUPPORTED_CURRENCIES:
        raise NormalizationError(f"unsupported_currency_format:currency:{currency}")
    return value


def _normalize_decimal_list_field(field_name: str, raw_value: object) -> List[Decimal]:
    if not isinstance(raw_value, list) or len(raw_value) == 0:
        raise NormalizationError(f"empty_or_invalid_list:{field_name}")
    values = []
    for i, item in enumerate(raw_value):
        decimal_value = _to_decimal_safe(item, f"{field_name}[{i}]")
        values.append(decimal_value)
    return values


def normalize_method(calc_def: CalculatorDefinition, method: Optional[str]) -> Optional[str]:
    if not calc_def.supported_methods:
        return None  # this calculator has no method/convention selection at all
    if method is None or method not in calc_def.supported_methods:
        raise NormalizationError(
            f"missing_or_unsupported_method: must be one of {calc_def.supported_methods}"
        )
    return method


def normalized_inputs_to_dict(normalized: List[NormalizedInput]) -> Dict[str, str]:
    return {ni.field_name: ni.normalized_value for ni in normalized}


def normalized_inputs_to_decimal_map(normalized: List[NormalizedInput]) -> Dict[str, object]:
    import json as _json
    result = {}
    for ni in normalized:
        if ni.normalized_unit == "boolean":
            result[ni.field_name] = ni.normalized_value == "true"
        elif ni.normalized_unit == "code":
            result[ni.field_name] = ni.normalized_value
        elif ni.normalized_unit == "decimal_list":
            result[ni.field_name] = [Decimal(v) for v in _json.loads(ni.normalized_value)]
        else:
            result[ni.field_name] = Decimal(ni.normalized_value)
    return result
