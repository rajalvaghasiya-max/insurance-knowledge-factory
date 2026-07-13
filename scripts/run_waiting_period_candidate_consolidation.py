from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.extraction_primitives.waiting_period_candidate_consolidator import (
    WaitingPeriodCandidateConsolidator,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolidate waiting-period evidence candidates without creating facts.")
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    result = WaitingPeriodCandidateConsolidator().consolidate(json.loads(input_path.read_text(encoding="utf-8")))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("=" * 70)
    print("WAITING PERIOD CANDIDATE CONSOLIDATION")
    print("=" * 70)
    print(f"Status             : {result['status']}")
    print(f"Input candidates   : {result['input_candidate_count']}")
    print(f"Consolidated groups: {result['consolidated_group_count']}")
    print(f"Output             : {output_path.resolve()}")
    print("NOTE: consolidated evidence only; no canonical facts or publication")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
