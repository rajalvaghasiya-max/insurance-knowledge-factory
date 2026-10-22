from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
from typing import Sequence

_PERCENT_RE = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*%")
_AMOUNT_RE = re.compile(
    r"(?:"
    r"₹\s*(?P<rupee_number>\d[\d,]*(?:\.\d+)?)\s*(?P<rupee_unit>crores?|cr|lakhs?|lacs?|k)?"
    r"|"
    r"(?P<unit_number>\d[\d,]*(?:\.\d+)?)\s*(?P<required_unit>crores?|cr|lakhs?|lacs?|k)\b"
    r")",
    re.IGNORECASE,
)

_UNIT_MULTIPLIER = {
    None: Decimal("1"),
    "k": Decimal("1000"),
    "lakh": Decimal("100000"),
    "lakhs": Decimal("100000"),
    "lac": Decimal("100000"),
    "lacs": Decimal("100000"),
    "crore": Decimal("10000000"),
    "crores": Decimal("10000000"),
    "cr": Decimal("10000000"),
}


@dataclass(frozen=True)
class ParsedPercentage:
    value: Decimal
    source_text: str


@dataclass(frozen=True)
class ParsedAmount:
    value: Decimal
    source_text: str


@dataclass(frozen=True)
class ArithmeticIllustration:
    operation: str
    text: str
    result_amount: Decimal


def _decimal(value: str) -> Decimal:
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation as exc:  # pragma: no cover - guarded by regex
        raise ValueError(f"invalid numeric value: {value!r}") from exc


def parse_percentages(text: str) -> tuple[ParsedPercentage, ...]:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return tuple(
        ParsedPercentage(value=_decimal(match.group(1)), source_text=match.group(0))
        for match in _PERCENT_RE.finditer(text)
    )


def parse_rupee_amounts(text: str) -> tuple[ParsedAmount, ...]:
    """Parse only explicitly monetary values: ₹-prefixed amounts or Indian money units."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    values: list[ParsedAmount] = []
    for match in _AMOUNT_RE.finditer(text):
        raw_number = match.group("rupee_number") or match.group("unit_number")
        unit = match.group("rupee_unit") or match.group("required_unit")
        normalized_unit = unit.lower() if unit else None
        multiplier = _UNIT_MULTIPLIER[normalized_unit]
        numeric = _decimal(raw_number) * multiplier
        if numeric <= 0:
            continue
        values.append(ParsedAmount(value=numeric, source_text=match.group(0).strip()))
    return tuple(values)


def _format_indian_integer(value: int) -> str:
    digits = str(abs(value))
    if len(digits) <= 3:
        grouped = digits
    else:
        grouped = digits[-3:]
        prefix = digits[:-3]
        pairs: list[str] = []
        while prefix:
            pairs.append(prefix[-2:])
            prefix = prefix[:-2]
        grouped = ",".join(reversed(pairs)) + "," + grouped
    return ("-" if value < 0 else "") + grouped


def format_inr(value: Decimal) -> str:
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    integral = value.to_integral_value()
    if value == integral:
        return "₹" + _format_indian_integer(int(integral))
    quantized = value.quantize(Decimal("0.01"))
    whole, fraction = f"{quantized:.2f}".split(".")
    return "₹" + _format_indian_integer(int(whole)) + "." + fraction


def percentage_of_amount(*, percentage: Decimal, amount: Decimal) -> Decimal:
    if percentage < 0 or amount < 0:
        raise ValueError("percentage and amount must be non-negative")
    return (percentage * amount / Decimal("100")).quantize(Decimal("0.01"))


def difference(*, larger: Decimal, smaller: Decimal) -> Decimal:
    if larger < 0 or smaller < 0:
        raise ValueError("amounts must be non-negative")
    if larger < smaller:
        raise ValueError("larger must be greater than or equal to smaller")
    return (larger - smaller).quantize(Decimal("0.01"))


def _latest_percentage(
    current_text: str,
    prior_customer_texts: Sequence[str],
) -> ParsedPercentage | None:
    current = parse_percentages(current_text)
    if len(current) == 1:
        return current[0]
    if len(current) > 1:
        return None
    for text in reversed(tuple(prior_customer_texts)):
        values = parse_percentages(text)
        if len(values) == 1:
            return values[0]
        if len(values) > 1:
            return None
    return None


def _single_amount(text: str) -> ParsedAmount | None:
    values = parse_rupee_amounts(text)
    return values[0] if len(values) == 1 else None


def build_percentage_illustration(
    *,
    current_text: str,
    prior_customer_texts: Sequence[str],
    basis_label: str,
    consequence_boundary: str,
    per_day: bool = False,
) -> ArithmeticIllustration | None:
    percentage = _latest_percentage(current_text, prior_customer_texts)
    amount = _single_amount(current_text)
    if percentage is None or amount is None:
        return None
    result = percentage_of_amount(percentage=percentage.value, amount=amount.value)
    suffix = " per day" if per_day else ""
    text = (
        f"Using only the numbers you gave: {percentage.source_text.strip()} of "
        f"{format_inr(amount.value)} is {format_inr(result)}{suffix}. "
        f"This uses {basis_label} only as the stated calculation basis. {consequence_boundary}"
    )
    return ArithmeticIllustration(
        operation="PERCENTAGE_OF_AMOUNT",
        text=text,
        result_amount=result,
    )


def build_difference_illustration(
    *,
    current_text: str,
    prior_customer_texts: Sequence[str],
    prior_percentage_basis_label: str,
    consequence_boundary: str,
) -> ArithmeticIllustration | None:
    current_amount = _single_amount(current_text)
    if current_amount is None:
        return None

    prior_texts = tuple(prior_customer_texts)
    for index in range(len(prior_texts) - 1, -1, -1):
        basis_amount = _single_amount(prior_texts[index])
        if basis_amount is None:
            continue
        percentage = _latest_percentage(prior_texts[index], prior_texts[:index])
        if percentage is None:
            continue
        calculated_limit = percentage_of_amount(
            percentage=percentage.value,
            amount=basis_amount.value,
        )
        if current_amount.value < calculated_limit:
            return None
        result = difference(larger=current_amount.value, smaller=calculated_limit)
        text = (
            f"Using only the numbers you gave: {format_inr(current_amount.value)} minus "
            f"{format_inr(calculated_limit)} is {format_inr(result)}. "
            f"The {format_inr(calculated_limit)} figure comes from {percentage.source_text.strip()} of "
            f"{format_inr(basis_amount.value)} using {prior_percentage_basis_label}. "
            f"{consequence_boundary}"
        )
        return ArithmeticIllustration(
            operation="DIFFERENCE",
            text=text,
            result_amount=result,
        )
    return None


__all__ = [
    "ArithmeticIllustration",
    "ParsedAmount",
    "ParsedPercentage",
    "build_difference_illustration",
    "build_percentage_illustration",
    "difference",
    "format_inr",
    "parse_percentages",
    "parse_rupee_amounts",
    "percentage_of_amount",
]
