"""
life_intelligence_lab.contracts
================================

Prototype-only data contracts for the AMFI NAV observation pipeline.

These shapes intentionally mirror -- but do NOT import from, and are not
identical to -- the `DynamicObservation` / `FundNAVObservation` contracts
described in PolicyScna's CLAUDE-LIFE-001/002/003 design documents. The
goal is that this prototype could later be adapted to sit behind those
governed contracts (as a real dynamic-data adapter) without a structural
redesign -- see ARCHITECTURE.md.

Field ordering in each dataclass is deliberate and fixed: it is the
ordering used when producing deterministic canonical output (see
`canonical.py`). Do not reorder fields casually.
"""

from __future__ import annotations

import dataclasses
from typing import List, Optional

ADAPTER_VERSION = "amfi-nav-adapter/0.1.0"
PARSER_VERSION = "amfi-nav-parser/0.1.0"

# Snapshot / download status vocabulary. Deliberately closed (not free text)
# so downstream code can branch on it reliably.
SNAPSHOT_STATUS_OK = "ok"
SNAPSHOT_STATUS_EMPTY_RESPONSE = "empty_response"
SNAPSHOT_STATUS_HTTP_ERROR = "http_error"
SNAPSHOT_STATUS_TIMEOUT = "timeout"

VALIDATION_STATUS_ACCEPTED = "accepted"


@dataclasses.dataclass(frozen=True)
class RawSnapshot:
    """
    Metadata describing one immutable raw download of the AMFI NAV source.

    The raw file bytes themselves are stored separately on disk at
    `raw_file_path`; this record is the manifest that makes that file
    inspectable and reproducible. `retrieval_timestamp` is the wall-clock
    time of the download and is NOT the same thing as any NAV valuation
    date found inside the file -- that distinction is made explicit at
    the observation level, never assumed here.
    """

    snapshot_id: str
    source_id: str
    source_url: str
    retrieval_timestamp: str  # ISO-8601 UTC, e.g. "2026-07-26T09:15:00+00:00"
    http_status: Optional[int]
    content_type: Optional[str]
    raw_file_path: Optional[str]
    raw_sha256: Optional[str]
    adapter_version: str
    status: str  # one of the SNAPSHOT_STATUS_* constants above
    warnings: List[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class RejectedRow:
    """
    A row from the raw source that could not be turned into a valid
    FundNAVObservation. Rejected rows are never silently dropped -- every
    one is recorded with a machine-readable `reason` and the exact
    original line text, so a human can audit exactly what was excluded
    and why.
    """

    line_number: int
    raw_line: str
    section: Optional[str]
    reason: str
    source_snapshot_id: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class FundNAVObservation:
    """
    A single canonical, validated AMFI mutual-fund NAV observation.

    `nav_value` is stored as a string (not a float) to preserve exact
    decimal precision from the source file end-to-end -- this is the
    decimal-safe representation required for any downstream monetary use.

    `nav_valuation_date` is normalized to ISO-8601 (YYYY-MM-DD) and is
    kept structurally distinct from `retrieval_timestamp`: the date the
    NAV is *for* is never the same field as the date it was *fetched*.
    """

    observation_id: str
    observation_type: str  # "mutual_fund_nav"
    amfi_scheme_code: str
    isin_payout_growth: Optional[str]
    isin_reinvestment: Optional[str]
    scheme_name: str
    category: Optional[str]
    nav_value: str
    currency: str
    nav_valuation_date: str
    retrieval_timestamp: str
    source_snapshot_id: str
    source_sha256: str
    adapter_version: str
    parser_version: str
    validation_status: str
    warnings: List[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


# Fixed field order used for canonical JSON serialization. Declared once,
# here, so contracts.py remains the single source of truth for both the
# dataclass shape and its serialized field order.
FUND_NAV_OBSERVATION_FIELD_ORDER = [
    "observation_id",
    "observation_type",
    "amfi_scheme_code",
    "isin_payout_growth",
    "isin_reinvestment",
    "scheme_name",
    "category",
    "nav_value",
    "currency",
    "nav_valuation_date",
    "retrieval_timestamp",
    "source_snapshot_id",
    "source_sha256",
    "adapter_version",
    "parser_version",
    "validation_status",
    "warnings",
]

RAW_SNAPSHOT_FIELD_ORDER = [
    "snapshot_id",
    "source_id",
    "source_url",
    "retrieval_timestamp",
    "http_status",
    "content_type",
    "raw_file_path",
    "raw_sha256",
    "adapter_version",
    "status",
    "warnings",
]

REJECTED_ROW_FIELD_ORDER = [
    "line_number",
    "raw_line",
    "section",
    "reason",
    "source_snapshot_id",
]
