"""
life_intelligence_lab.calculators.output_writer
==================================================

Writes a (CalculationResult, CalculationTrace) pair to disk as
`result.json` and `trace.json` -- both fully deterministic content, byte
-identical across repeated runs over the same request -- plus a separate
`run_metadata.json` carrying the one piece of genuinely non-deterministic
information (the wall-clock time this particular CLI invocation ran),
kept out of the hashed/deterministic files entirely. This mirrors the
LIFE-PROTOTYPE-001 AMFI adapter's canonical-output pattern, reimplemented
here rather than imported, per the "no AMFI-specific dependency" boundary.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

from life_intelligence_lab.calculators import canonical, serialization
from life_intelligence_lab.calculators.contracts import (
    CALCULATION_RESULT_FIELD_ORDER,
    CALCULATION_TRACE_FIELD_ORDER,
    CalculationResult,
    CalculationTrace,
)

RESULT_FILENAME = "result.json"
TRACE_FILENAME = "trace.json"
RUN_METADATA_FILENAME = "run_metadata.json"


def write_calculation_output(
    result: CalculationResult,
    trace: Optional[CalculationTrace],
    output_dir: str,
    run_label: str = "run",
) -> dict:
    os.makedirs(output_dir, exist_ok=True)

    result_dict = serialization.result_to_dict(result)
    result_json = json.dumps(result_dict, ensure_ascii=False, indent=2, sort_keys=False)
    with open(os.path.join(output_dir, RESULT_FILENAME), "w", encoding="utf-8") as fh:
        fh.write(result_json)
        fh.write("\n")
    result_content_hash = canonical.hash_result_content(result_dict, CALCULATION_RESULT_FIELD_ORDER)

    trace_content_hash = None
    if trace is not None:
        trace_dict = serialization.trace_to_dict(trace)
        trace_json = json.dumps(trace_dict, ensure_ascii=False, indent=2, sort_keys=False)
        with open(os.path.join(output_dir, TRACE_FILENAME), "w", encoding="utf-8") as fh:
            fh.write(trace_json)
            fh.write("\n")
        trace_content_hash = canonical.hash_trace_content(trace_dict, CALCULATION_TRACE_FIELD_ORDER)

    run_metadata = {
        "run_label": run_label,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(os.path.join(output_dir, RUN_METADATA_FILENAME), "w", encoding="utf-8") as fh:
        json.dump(run_metadata, fh, indent=2, sort_keys=True)
        fh.write("\n")

    return {
        "result_content_hash": result_content_hash,
        "trace_content_hash": trace_content_hash,
        "input_hash": result.deterministic_input_hash,
        "output_hash": result.deterministic_output_hash,
    }


def load_calculation_output(output_dir: str) -> dict:
    with open(os.path.join(output_dir, RESULT_FILENAME), "r", encoding="utf-8") as fh:
        result_dict = json.load(fh)
    result_content_hash = canonical.hash_result_content(result_dict, CALCULATION_RESULT_FIELD_ORDER)

    trace_content_hash = None
    trace_path = os.path.join(output_dir, TRACE_FILENAME)
    if os.path.exists(trace_path):
        with open(trace_path, "r", encoding="utf-8") as fh:
            trace_dict = json.load(fh)
        trace_content_hash = canonical.hash_trace_content(trace_dict, CALCULATION_TRACE_FIELD_ORDER)

    return {
        "result_content_hash": result_content_hash,
        "trace_content_hash": trace_content_hash,
        "input_hash": result_dict.get("deterministic_input_hash"),
        "output_hash": result_dict.get("deterministic_output_hash"),
    }
