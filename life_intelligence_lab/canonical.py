"""
life_intelligence_lab.canonical
================================

Writes parsed AMFI NAV results to deterministic canonical output.

Determinism contract: given the same raw snapshot content, calling
`write_canonical_outputs` must always produce byte-identical
`observations.jsonl` and `rejected.jsonl` files (and therefore identical
SHA-256 hashes), regardless of when or how many times it is run. This is
what `scripts/replay_amfi_nav.py` proves.

To make that possible, anything that is NOT deterministic (the wall-clock
time a parse/replay command happened to run, the host that ran it) is
written to a separate `run_metadata.json` file, never mixed into the
canonical record content itself.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import List

from life_intelligence_lab.contracts import (
    FUND_NAV_OBSERVATION_FIELD_ORDER,
    FundNAVObservation,
    REJECTED_ROW_FIELD_ORDER,
    RejectedRow,
)
from life_intelligence_lab.parser import ParseResult

OBSERVATIONS_FILENAME = "observations.jsonl"
REJECTED_FILENAME = "rejected.jsonl"
SUMMARY_FILENAME = "summary.json"
RUN_METADATA_FILENAME = "run_metadata.json"


def _dumps_ordered(obj_dict: dict, field_order: List[str]) -> str:
    ordered = {field: obj_dict[field] for field in field_order}
    return json.dumps(ordered, ensure_ascii=False, separators=(",", ":"), sort_keys=False)


def _observations_to_jsonl(observations: List[FundNAVObservation]) -> str:
    # Records are already sorted deterministically by the parser; sort
    # again here defensively so this function's determinism guarantee
    # does not silently depend on caller behaviour.
    ordered = sorted(
        observations,
        key=lambda o: (o.amfi_scheme_code, o.nav_valuation_date, o.isin_payout_growth or ""),
    )
    lines = [_dumps_ordered(o.to_dict(), FUND_NAV_OBSERVATION_FIELD_ORDER) for o in ordered]
    return "\n".join(lines) + ("\n" if lines else "")


def _rejected_to_jsonl(rejected: List[RejectedRow]) -> str:
    ordered = sorted(rejected, key=lambda r: r.line_number)
    lines = [_dumps_ordered(r.to_dict(), REJECTED_ROW_FIELD_ORDER) for r in ordered]
    return "\n".join(lines) + ("\n" if lines else "")


def write_canonical_outputs(result: ParseResult, output_dir: str, run_label: str = "run") -> dict:
    """
    Writes observations.jsonl, rejected.jsonl, summary.json (all
    deterministic / content-derived) and run_metadata.json (wall-clock,
    non-deterministic, kept separate) under `output_dir`.

    Returns a dict with the SHA-256 hashes of the two deterministic
    content files, which is what proves replay determinism.
    """
    os.makedirs(output_dir, exist_ok=True)

    observations_content = _observations_to_jsonl(result.accepted)
    rejected_content = _rejected_to_jsonl(result.rejected)

    observations_path = os.path.join(output_dir, OBSERVATIONS_FILENAME)
    rejected_path = os.path.join(output_dir, REJECTED_FILENAME)

    with open(observations_path, "w", encoding="utf-8") as fh:
        fh.write(observations_content)
    with open(rejected_path, "w", encoding="utf-8") as fh:
        fh.write(rejected_content)

    observations_sha256 = hashlib.sha256(observations_content.encode("utf-8")).hexdigest()
    rejected_sha256 = hashlib.sha256(rejected_content.encode("utf-8")).hexdigest()

    # summary.json is derived purely from record *counts and reasons*,
    # which are themselves deterministic content -- so it is written as
    # deterministic output too (no timestamps inside it).
    summary = dict(result.summary)
    summary["observations_sha256"] = observations_sha256
    summary["rejected_sha256"] = rejected_sha256
    summary_path = os.path.join(output_dir, SUMMARY_FILENAME)
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True)
        fh.write("\n")

    # run_metadata.json is intentionally the ONLY file in this directory
    # allowed to contain "now" -- it must never be read by anything that
    # needs deterministic output, only by humans auditing when a run happened.
    run_metadata = {
        "run_label": run_label,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(os.path.join(output_dir, RUN_METADATA_FILENAME), "w", encoding="utf-8") as fh:
        json.dump(run_metadata, fh, indent=2, sort_keys=True)
        fh.write("\n")

    return {
        "observations_sha256": observations_sha256,
        "rejected_sha256": rejected_sha256,
        "observations_path": observations_path,
        "rejected_path": rejected_path,
        "summary_path": summary_path,
    }
