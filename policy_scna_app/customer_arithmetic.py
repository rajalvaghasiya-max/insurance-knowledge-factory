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


def build_conditional_percentage_illustration(
    *,
    current_text: str,
    prior_customer_texts: Sequence[str],
    consequence_boundary: str,
) -> ArithmeticIllustration | None:
    """Calculate each explicit current amount conditionally without choosing an authoritative base."""
    percentage = _latest_percentage(current_text, prior_customer_texts)
    amounts = parse_rupee_amounts(current_text)
    if percentage is None or len(amounts) < 2:
        return None

    unique: list[ParsedAmount] = []
    seen: set[Decimal] = set()
    for amount in amounts:
        if amount.value in seen:
            continue
        seen.add(amount.value)
        unique.append(amount)
    if len(unique) < 2 or len(unique) > 3:
        return None

    clauses: list[str] = []
    results: list[Decimal] = []
    for amount in unique:
        result = percentage_of_amount(percentage=percentage.value, amount=amount.value)
        results.append(result)
        clauses.append(
            f"if {format_inr(amount.value)} is the applicable calculation base, "
            f"{percentage.source_text.strip()} is {format_inr(result)}"
        )

    text = (
        "Using only the numbers you gave: "
        + "; ".join(clauses)
        + ". I am not choosing which amount is the policy's actual calculation base. "
        + consequence_boundary
    )
    return ArithmeticIllustration(
        operation="CONDITIONAL_PERCENTAGE_OF_AMOUNTS",
        text=text,
        result_amount=results[-1],
    )


def _derived_prior_limit(prior_customer_texts: Sequence[str]) -> Decimal | None:
    prior_texts = tuple(prior_customer_texts)
    for index in range(len(prior_texts) - 1, -1, -1):
        basis_amount = _single_amount(prior_texts[index])
        if basis_amount is None:
            continue
        percentage = _latest_percentage(prior_texts[index], prior_texts[:index])
        if percentage is None:
            continue
        return percentage_of_amount(
            percentage=percentage.value,
            amount=basis_amount.value,
        )
    return None


def build_difference_illustration(
    *,
    current_text: str,
    prior_customer_texts: Sequence[str],
    prior_percentage_basis_label: str,
    consequence_boundary: str,
) -> ArithmeticIllustration | None:
    calculated_limit = _derived_prior_limit(prior_customer_texts)
    if calculated_limit is None:
        return None

    current_amounts = parse_rupee_amounts(current_text)
    if not current_amounts:
        return None

    larger_candidates = [amount for amount in current_amounts if amount.value > calculated_limit]
    if not larger_candidates:
        return None

    selected: ParsedAmount | None = None
    if len(larger_candidates) == 1:
        selected = larger_candidates[0]
    else:
        supplied_values = {amount.value for amount in current_amounts}
        self_verifying = [
            amount
            for amount in larger_candidates
            if difference(larger=amount.value, smaller=calculated_limit) in supplied_values
        ]
        if len(self_verifying) == 1:
            selected = self_verifying[0]
    if selected is None:
        return None

    result = difference(larger=selected.value, smaller=calculated_limit)
    text = (
        f"Using only the numbers you gave: {format_inr(selected.value)} minus "
        f"{format_inr(calculated_limit)} is {format_inr(result)}. "
        f"The {format_inr(calculated_limit)} figure comes from the earlier customer-supplied "
        f"percentage and amount using {prior_percentage_basis_label}. {consequence_boundary}"
    )
    return ArithmeticIllustration(
        operation="DIFFERENCE",
        text=text,
        result_amount=result,
    )


__all__ = [
    "ArithmeticIllustration",
    "ParsedAmount",
    "ParsedPercentage",
    "build_conditional_percentage_illustration",
    "build_difference_illustration",
    "build_percentage_illustration",
    "difference",
    "format_inr",
    "parse_percentages",
    "parse_rupee_amounts",
    "percentage_of_amount",
]
