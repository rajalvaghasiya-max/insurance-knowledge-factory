"""
life_intelligence_lab.parser
=============================

Parses the AMFI daily NAV flat-file format into canonical
`FundNAVObservation` records.

This module performs NO network access. It only ever reads a local raw
snapshot's text content, already retrieved by `downloader.py`.

AMFI's format (illustrative):

    Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date
    <blank line>
    Open Ended Schemes(Overnight Fund)
    <blank line>
    118551;INF209K01UN8;-;Axis Overnight Fund - Regular Plan - Growth;1234.5678;25-Jul-2026
    118552;INF209K01UO6;INF209K01UP3;Axis Overnight Fund - Regular Plan - IDCW;1050.1234;25-Jul-2026
    <blank line>
    Open Ended Schemes(Liquid Fund)
    ...

Section headings are lines with no semicolons; data rows have semicolons;
blank lines are pure separators, not errors. The parser tracks the most
recently seen section heading and attaches it to every observation and
rejected row parsed after it, until the next heading.
"""

from __future__ import annotations

import dataclasses
import hashlib
from typing import List, Optional

from life_intelligence_lab.contracts import (
    ADAPTER_VERSION,
    FundNAVObservation,
    PARSER_VERSION,
    RawSnapshot,
    RejectedRow,
    VALIDATION_STATUS_ACCEPTED,
)
from life_intelligence_lab.validation import ValidationError, normalize_isin
from life_intelligence_lab.validation import validate_nav
from life_intelligence_lab.validation import validate_nav_date
from life_intelligence_lab.validation import validate_scheme_code
from life_intelligence_lab.validation import validate_scheme_name

_HEADER_LINE_PREFIX = "Scheme Code"
_CURRENCY = "INR"
_MIN_DATA_FIELDS = 6


@dataclasses.dataclass(frozen=True)
class ParseResult:
    accepted: List[FundNAVObservation]
    rejected: List[RejectedRow]

    @property
    def summary(self) -> dict:
        reason_counts: dict = {}
        for row in self.rejected:
            reason_counts[row.reason] = reason_counts.get(row.reason, 0) + 1
        return {
            "accepted_count": len(self.accepted),
            "rejected_count": len(self.rejected),
            "rejected_by_reason": dict(sorted(reason_counts.items())),
        }


def _make_observation_id(scheme_code: str, nav_date: str, isin_payout: Optional[str]) -> str:
    """
    Deterministic (content-derived, not random) observation id, so that
    repeated parses of the same snapshot produce byte-identical
    observation ids and therefore byte-identical canonical output.
    """
    key = f"{scheme_code}|{nav_date}|{isin_payout or ''}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return f"obs_{digest}"


def parse_amfi_nav(raw_text: str, snapshot: RawSnapshot) -> ParseResult:
    """
    Parse raw AMFI NAV text into accepted observations and rejected rows.

    Deterministic ordering: the returned `accepted` list is sorted by
    (amfi_scheme_code, nav_valuation_date, isin_payout_growth) regardless
    of the order rows appeared in the source file, so canonical output
    never depends on incidental source ordering.
    """
    accepted: List[FundNAVObservation] = []
    rejected: List[RejectedRow] = []
    # Maps a dedupe key -> the line number of the first accepted occurrence,
    # so later duplicates can be rejected with a specific, useful reason.
    seen_keys: dict = {}

    current_section: Optional[str] = None

    lines = raw_text.splitlines()
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip("\r\n")
        stripped = line.strip()

        if not stripped:
            continue  # blank line: section separator, not an error

        if ";" not in line:
            # A line with no delimiters is a category / section heading,
            # e.g. "Open Ended Schemes(Overnight Fund)".
            current_section = stripped
            continue

        if line.startswith(_HEADER_LINE_PREFIX):
            continue  # repeated or single column-header row: not data

        fields = line.split(";")
        if len(fields) < _MIN_DATA_FIELDS:
            rejected.append(
                RejectedRow(
                    line_number=line_number,
                    raw_line=raw_line,
                    section=current_section,
                    reason=(
                        f"malformed_row: expected at least {_MIN_DATA_FIELDS} "
                        f"semicolon-delimited fields, got {len(fields)}"
                    ),
                    source_snapshot_id=snapshot.snapshot_id,
                )
            )
            continue

        (
            scheme_code_raw,
            isin_payout_raw,
            isin_reinvest_raw,
            scheme_name_raw,
            nav_raw,
            date_raw,
        ) = fields[:6]

        row_warnings: List[str] = []

        try:
            scheme_code = validate_scheme_code(scheme_code_raw)
            scheme_name = validate_scheme_name(scheme_name_raw)
            nav = validate_nav(nav_raw)
            nav_date = validate_nav_date(date_raw)
        except ValidationError as exc:
            rejected.append(
                RejectedRow(
                    line_number=line_number,
                    raw_line=raw_line,
                    section=current_section,
                    reason=str(exc),
                    source_snapshot_id=snapshot.snapshot_id,
                )
            )
            continue

        isin_payout, isin_payout_warning = normalize_isin(isin_payout_raw)
        if isin_payout_warning:
            row_warnings.append(isin_payout_warning)
        isin_reinvest, isin_reinvest_warning = normalize_isin(isin_reinvest_raw)
        if isin_reinvest_warning:
            row_warnings.append(isin_reinvest_warning)

        dedupe_key = (scheme_code, nav_date, isin_payout or "")
        if dedupe_key in seen_keys:
            rejected.append(
                RejectedRow(
                    line_number=line_number,
                    raw_line=raw_line,
                    section=current_section,
                    reason=(
                        f"duplicate_row: same scheme_code/nav_date/isin as "
                        f"line {seen_keys[dedupe_key]}"
                    ),
                    source_snapshot_id=snapshot.snapshot_id,
                )
            )
            continue
        seen_keys[dedupe_key] = line_number

        observation = FundNAVObservation(
            observation_id=_make_observation_id(scheme_code, nav_date, isin_payout),
            observation_type="mutual_fund_nav",
            amfi_scheme_code=scheme_code,
            isin_payout_growth=isin_payout,
            isin_reinvestment=isin_reinvest,
            scheme_name=scheme_name,
            category=current_section,
            nav_value=str(nav),
            currency=_CURRENCY,
            nav_valuation_date=nav_date,
            retrieval_timestamp=snapshot.retrieval_timestamp,
            source_snapshot_id=snapshot.snapshot_id,
            source_sha256=snapshot.raw_sha256 or "",
            adapter_version=ADAPTER_VERSION,
            parser_version=PARSER_VERSION,
            validation_status=VALIDATION_STATUS_ACCEPTED,
            warnings=row_warnings,
        )
        accepted.append(observation)

    accepted.sort(
        key=lambda o: (o.amfi_scheme_code, o.nav_valuation_date, o.isin_payout_growth or "")
    )
    rejected.sort(key=lambda r: r.line_number)

    return ParseResult(accepted=accepted, rejected=rejected)
