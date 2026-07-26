"""
Usage:
    python -m life_intelligence_lab.scripts.replay_calculation \\
        --request examples/fv_request.json \\
        [--compare-to life_intelligence_lab/data/calculations/<request_id>] \\
        [--out-dir DIR]

Re-executes the SAME CalculationRequest JSON file through the identical
deterministic runtime code path as run_calculator.py, writes a fresh
result.json/trace.json, and (if --compare-to is given) proves that the
result content hash, trace content hash, input hash, and output hash are
all byte-for-byte identical to a prior run over the same request.

There is no separate "replay implementation" to drift from the original
-- replay_calculation.py and run_calculator.py both call
`execute_calculation_request()` from the same `runtime.py` module. What
this script proves is that calling it again, independently, produces the
same result -- not that a different code path agrees with the first one.
"""

from __future__ import annotations

import argparse
import json
import sys

from life_intelligence_lab.calculators.output_writer import load_calculation_output, write_calculation_output
from life_intelligence_lab.calculators.runtime import execute_calculation_request

DEFAULT_OUT_ROOT = "life_intelligence_lab/data/calculations_replay"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Deterministically replay a CalculationRequest.")
    parser.add_argument("--request", required=True, help="Path to the CalculationRequest JSON file")
    parser.add_argument("--compare-to", default=None, help="Path to a prior output dir to compare hashes against")
    parser.add_argument("--out-dir", default=None, help="Output directory (default: data/calculations_replay/<request_id>)")
    args = parser.parse_args(argv)

    with open(args.request, "r", encoding="utf-8") as fh:
        request = json.load(fh)

    result, trace = execute_calculation_request(request)
    out_dir = args.out_dir or f"{DEFAULT_OUT_ROOT}/{request.get('request_id', 'unknown_request')}"
    hashes = write_calculation_output(result, trace, out_dir, run_label="replay")

    print("Replay complete.")
    print(f"  status: {result.status}")
    print(f"  input_hash: {hashes['input_hash']}")
    print(f"  output_hash: {hashes['output_hash']}")
    print(f"  result_content_hash: {hashes['result_content_hash']}")
    print(f"  trace_content_hash: {hashes['trace_content_hash']}")

    if args.compare_to:
        prior = load_calculation_output(args.compare_to)
        checks = {
            "input_hash": prior["input_hash"] == hashes["input_hash"],
            "output_hash": prior["output_hash"] == hashes["output_hash"],
            "result_content_hash": prior["result_content_hash"] == hashes["result_content_hash"],
            "trace_content_hash": prior["trace_content_hash"] == hashes["trace_content_hash"],
        }
        if all(checks.values()):
            print("  DETERMINISTIC REPLAY: MATCH (all hashes identical to prior run)")
            return 0
        else:
            print("  DETERMINISTIC REPLAY: MISMATCH", file=sys.stderr)
            for name, ok in checks.items():
                print(f"    {name}: {'match' if ok else 'MISMATCH'}", file=sys.stderr)
            return 1

    return 0 if result.status == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
