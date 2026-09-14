"""Pure deterministic waiting-period applicability helpers.

No I/O, no product identifiers, and no claim-approval authority. This module only
compares approved case dates against governed waiting-period duration semantics.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
import re


class WaitingPeriodApplicabilityError(ValueError):
    """Raised when governed duration or approved case dates cannot be resolved safely."""


_DURATION = re.compile(r"(?<!\d)(\d+)\s*(day|days|month|months|year|years)\b", re.I)


@dataclass(frozen=True)
class WaitingPeriodTimelineResolution:
    start_date: date
    event_date: date
    boundary_date: date
    status: str


def parse_governed_duration(text: str) -> tuple[int, str]:
    matches = [(int(value), unit.lower()) for value, unit in _DURATION.findall(text)]
    normalized = {(value, unit.rstrip("s") + "s") for value, unit in matches}
    if len(normalized) != 1:
        raise WaitingPeriodApplicabilityError(
            "waiting-period duration must contain exactly one unambiguous governed duration"
        )
    value, unit = next(iter(normalized))
    if value <= 0:
        raise WaitingPeriodApplicabilityError("waiting-period duration must be greater than zero")
    return value, unit


def parse_iso_date(value: object, *, label: str) -> date:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodApplicabilityError(f"{label} must be a non-empty ISO date string")
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise WaitingPeriodApplicabilityError(f"{label} must be YYYY-MM-DD") from exc


def add_duration(start: date, value: int, unit: str) -> date:
    if unit == "days":
        return start + timedelta(days=value)
    if unit == "months":
        month_index = start.month - 1 + value
        year = start.year + month_index // 12
        month = month_index % 12 + 1
        day = min(start.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    if unit == "years":
        year = start.year + value
        day = min(start.day, calendar.monthrange(year, start.month)[1])
        return date(year, start.month, day)
    raise WaitingPeriodApplicabilityError(f"unsupported waiting-period unit: {unit}")


def resolve_timeline(*, start_date: object, event_date: object, duration_text: str) -> WaitingPeriodTimelineResolution:
    """Resolve only dates safely away from the activation-convention boundary.

    Governed wording may establish a duration without establishing whether coverage
    activates on the calculated boundary date or only after it. Therefore:
    - event before boundary -> waiting period definitely NOT_COMPLETE;
    - event after boundary -> waiting period definitely COMPLETE;
    - event exactly on boundary -> unresolved and fail closed.
    """
    start = parse_iso_date(start_date, label="policy_start_date")
    event = parse_iso_date(event_date, label="claim_date")
    if event < start:
        raise WaitingPeriodApplicabilityError("claim_date cannot be earlier than policy_start_date")
    value, unit = parse_governed_duration(duration_text)
    boundary = add_duration(start, value, unit)
    if event < boundary:
        status = "NOT_COMPLETE"
    elif event > boundary:
        status = "COMPLETE"
    else:
        status = "BOUNDARY_UNRESOLVED"
    return WaitingPeriodTimelineResolution(start, event, boundary, status)


__all__ = [
    "WaitingPeriodApplicabilityError",
    "WaitingPeriodTimelineResolution",
    "add_duration",
    "parse_governed_duration",
    "parse_iso_date",
    "resolve_timeline",
]
