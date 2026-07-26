"""
life_intelligence_lab.calculators.cash_flow
==============================================

Normalizes a raw list of dated cash-flow dicts (as given in a
CalculationRequest's `cash_flows` field) into a canonical, deterministically
-ordered list of `CashFlow` records, applying the request's duplicate
-date policy explicitly.

Nothing here infers a missing date, amount, or currency, and nothing
here silently nets duplicate dates -- `NET_SAME_DATE` only ever applies
when the caller has explicitly selected it, and every netting operation
performed is recorded, never just applied invisibly.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from decimal import Decimal
from typing import Dict, List, Tuple

from life_intelligence_lab.calculators.contracts import (
    CashFlow,
    DUPLICATE_DATE_POLICY_NET,
    DUPLICATE_DATE_POLICY_REJECT,
    DuplicateDateOperation,
)
from life_intelligence_lab.calculators.normalization import (
    NormalizationError,
    SUPPORTED_CURRENCIES,
    to_decimal_safe,
    validate_iso_date,
)


def _derive_cash_flow_id(date: str, amount: str, currency: str, source_type: str, source_reference, description) -> str:
    """
    Deterministic, content-derived id -- never random (see contracts.CashFlow
    docstring). Deliberately does NOT depend on `sequence`: sequence
    reflects the flow's position in the *original, possibly arbitrarily
    -ordered* input list, and section 7 requires that "[o]riginal ordering
    must not affect canonical output after normalisation" -- an id that
    changed depending on input order would silently violate that
    (verified by `test_cash_flow_order_permutation_does_not_change_hash`).
    Two flows are only assigned the same id if every one of these fields
    is identical, which correctly reflects that there is no recorded
    information distinguishing them.
    """
    key = f"{date}|{amount}|{currency}|{source_type}|{source_reference or ''}|{description or ''}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
    return f"cf_{digest}"


def _derive_net_cash_flow_id(date: str, original_ids: List[str]) -> str:
    key = f"net|{date}|{'|'.join(sorted(original_ids))}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
    return f"cf_net_{digest}"


def cash_flow_to_dict(cf: CashFlow) -> dict:
    from life_intelligence_lab.calculators.contracts import CASH_FLOW_FIELD_ORDER
    full = {
        "cash_flow_id": cf.cash_flow_id, "date": cf.date, "amount": cf.amount,
        "currency": cf.currency, "source_type": cf.source_type,
        "source_reference": cf.source_reference, "description": cf.description,
        "sequence": cf.sequence,
    }
    return {k: full[k] for k in CASH_FLOW_FIELD_ORDER}


def cash_flow_to_hashable_dict(cf: CashFlow) -> dict:
    """
    Same content as `cash_flow_to_dict`, deliberately WITHOUT `sequence`.

    `sequence` records the flow's position in the original, possibly
    arbitrarily-ordered input list -- useful trace provenance for a human
    reader, but not economically meaningful: two cash-flow sets with
    identical dates/amounts/currencies/source_types entered in a
    different order describe the same calculation and MUST hash
    identically (section 7's "[o]riginal ordering must not affect
    canonical output after normalisation", exercised by
    `test_cash_flow_order_permutation_does_not_change_hash`). Including
    `sequence` in hashed content would silently violate that. The full,
    sequence-inclusive `cash_flow_to_dict` is still what's stored in the
    human-readable trace -- only the HASH basis excludes it.
    """
    d = cash_flow_to_dict(cf)
    return {k: v for k, v in d.items() if k != "sequence"}


def duplicate_operation_to_dict(op: DuplicateDateOperation) -> dict:
    from life_intelligence_lab.calculators.contracts import DUPLICATE_DATE_OPERATION_FIELD_ORDER
    full = {
        "date": op.date, "original_cash_flow_ids": op.original_cash_flow_ids,
        "original_amounts": op.original_amounts, "net_amount": op.net_amount, "note": op.note,
    }
    return {k: full[k] for k in DUPLICATE_DATE_OPERATION_FIELD_ORDER}


def normalize_single_cash_flow(raw: dict, sequence: int) -> CashFlow:
    if not isinstance(raw, dict):
        raise NormalizationError(f"malformed_cash_flow:index_{sequence}: expected an object")

    if "date" not in raw or raw["date"] in (None, ""):
        raise NormalizationError(f"missing_required_input:cash_flows[{sequence}].date")
    if "amount" not in raw or raw["amount"] in (None, ""):
        raise NormalizationError(f"missing_required_input:cash_flows[{sequence}].amount")
    if "currency" not in raw or not raw["currency"]:
        raise NormalizationError(f"missing_required_input:cash_flows[{sequence}].currency")
    if "source_type" not in raw or not raw["source_type"]:
        raise NormalizationError(f"missing_required_input:cash_flows[{sequence}].source_type")

    date = validate_iso_date(raw["date"], f"cash_flows[{sequence}].date")
    amount_decimal = to_decimal_safe(raw["amount"], f"cash_flows[{sequence}].amount")
    if not amount_decimal.is_finite():
        raise NormalizationError(f"non_finite_value:cash_flows[{sequence}].amount")

    currency_raw = raw["currency"]
    if not isinstance(currency_raw, str) or not currency_raw.strip():
        raise NormalizationError(f"unsupported_currency_format:cash_flows[{sequence}].currency")
    currency = currency_raw.strip().upper()
    if currency not in SUPPORTED_CURRENCIES:
        raise NormalizationError(f"unsupported_currency_format:cash_flows[{sequence}].currency:{currency_raw}")

    source_type = str(raw["source_type"]).strip()
    if not source_type:
        raise NormalizationError(f"missing_required_input:cash_flows[{sequence}].source_type")

    source_reference = raw.get("source_reference")
    if source_reference is not None:
        source_reference = str(source_reference)
    description = raw.get("description")
    if description is not None:
        description = str(description)

    amount_str = str(amount_decimal)
    cash_flow_id = _derive_cash_flow_id(date, amount_str, currency, source_type, source_reference, description)

    return CashFlow(
        cash_flow_id=cash_flow_id,
        date=date,
        amount=amount_str,
        currency=currency,
        source_type=source_type,
        source_reference=source_reference,
        description=description,
        sequence=sequence,
    )


def normalize_cash_flow_list(
    raw_list: List[dict], duplicate_date_policy: str
) -> Tuple[List[CashFlow], List[DuplicateDateOperation], str]:
    """
    Returns (normalized_cash_flows, duplicate_date_operations, currency).

    `normalized_cash_flows` is sorted by (date, sequence) -- deterministic
    regardless of the order flows were supplied in the request (section
    7's "[o]riginal ordering must not affect canonical output after
    normalisation" and section 18's "cash-flow ordering permutations"
    adversarial case).
    """
    if duplicate_date_policy not in (DUPLICATE_DATE_POLICY_REJECT, DUPLICATE_DATE_POLICY_NET):
        raise NormalizationError(f"unsupported_duplicate_date_policy:{duplicate_date_policy}")

    if not isinstance(raw_list, list) or len(raw_list) == 0:
        raise NormalizationError("empty_cash_flow_list")

    individual: List[CashFlow] = [
        normalize_single_cash_flow(raw, sequence=i) for i, raw in enumerate(raw_list)
    ]

    currencies = {cf.currency for cf in individual}
    if len(currencies) > 1:
        raise NormalizationError(f"mixed_currencies:{sorted(currencies)}")
    currency = next(iter(currencies))

    # Group by normalized date, preserving each group's original relative order.
    by_date: "OrderedDict[str, List[CashFlow]]" = OrderedDict()
    for cf in individual:
        by_date.setdefault(cf.date, []).append(cf)

    duplicate_dates = {date: flows for date, flows in by_date.items() if len(flows) > 1}

    if duplicate_dates and duplicate_date_policy == DUPLICATE_DATE_POLICY_REJECT:
        first_dup_date = next(iter(duplicate_dates))
        raise NormalizationError(f"duplicate_date_rejected:{first_dup_date}")

    normalized: List[CashFlow] = []
    operations: List[DuplicateDateOperation] = []

    for date, flows in by_date.items():
        if len(flows) == 1:
            normalized.append(flows[0])
            continue

        # duplicate_date_policy == NET_SAME_DATE
        net_amount = sum((Decimal(cf.amount) for cf in flows), Decimal(0))
        original_ids = [cf.cash_flow_id for cf in flows]
        original_amounts = [cf.amount for cf in flows]
        net_id = _derive_net_cash_flow_id(date, original_ids)
        note = (
            f"netted {len(flows)} same-date flows per NET_SAME_DATE policy"
            + (" (net amount is exactly zero -- retained explicitly, not dropped)" if net_amount == 0 else "")
        )
        operations.append(DuplicateDateOperation(
            date=date,
            original_cash_flow_ids=original_ids,
            original_amounts=original_amounts,
            net_amount=str(net_amount),
            note=note,
        ))
        # min sequence among the netted group, for stable tie-break ordering
        min_sequence = min(cf.sequence for cf in flows)
        normalized.append(CashFlow(
            cash_flow_id=net_id,
            date=date,
            amount=str(net_amount),
            currency=currency,
            source_type="netted",
            source_reference=None,
            description=f"Net of {len(flows)} same-date flows: {', '.join(original_ids)}",
            sequence=min_sequence,
        ))

    normalized.sort(key=lambda cf: (cf.date, cf.sequence))

    return normalized, operations, currency
