"""
Usage:
    python -m life_intelligence_lab.scripts.run_calculator \\
        --calculator FV_LUMP_SUM --version 1 --input examples/fv_request.json \\
        [--out-dir DIR]

Executes ONE CalculationRequest (loaded from a JSON file) against the
registered calculator runtime and writes result.json + trace.json (if
successful) to --out-dir.

--calculator/--version are a sanity check, not an override: if given,
they must match the calculator_id/calculator_version already present
inside the --input JSON file, or the command refuses to run rather than
silently executing against a different calculator than the file names.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from life_intelligence_lab.calculators.output_writer import write_calculation_output
from life_intelligence_lab.calculators.runtime import execute_calculation_request

DEFAULT_OUT_ROOT = "life_intelligence_lab/data/calculations"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run a CalculationRequest against a registered calculator.")
    parser.add_argument("--calculator", required=False, help="Expected calculator_id (sanity check against --input)")
    parser.add_argument("--version", type=int, required=False, help="Expected calculator_version (sanity check)")
    parser.add_argument("--input", required=True, help="Path to a CalculationRequest JSON file")
    parser.add_argument("--out-dir", default=None, help="Output directory (default: data/calculations/<request_id>)")
    args = parser.parse_args(argv)

    with open(args.input, "r", encoding="utf-8") as fh:
        request = json.load(fh)

    if args.calculator is not None and request.get("calculator_id") != args.calculator:
        print(
            f"REFUSING TO RUN: --calculator {args.calculator} does not match "
            f"calculator_id '{request.get('calculator_id')}' in {args.input}",
            file=sys.stderr,
        )
        return 1
    if args.version is not None and request.get("calculator_version") != args.version:
        print(
            f"REFUSING TO RUN: --version {args.version} does not match "
            f"calculator_version {request.get('calculator_version')} in {args.input}",
            file=sys.stderr,
        )
        return 1

    result, trace = execute_calculation_request(request)
    out_dir = args.out_dir or os.path.join(DEFAULT_OUT_ROOT, request.get("request_id", "unknown_request"))
    hashes = write_calculation_output(result, trace, out_dir, run_label="run")

    print(f"Status: {result.status}")
    if result.reason:
        print(f"Reason: {result.reason}")
    if result.status == "SUCCESS":
        print(f"Output: {result.output_values}")
        print(f"Warnings: {result.warnings}")
    print(f"Input hash: {hashes['input_hash']}")
    print(f"Output hash: {hashes['output_hash']}")
    print(f"Output dir: {out_dir}")

    return 0 if result.status == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
