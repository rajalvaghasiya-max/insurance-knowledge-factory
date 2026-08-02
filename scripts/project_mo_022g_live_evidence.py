"""Project a local MO-022G live trace into governed, non-certifying evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from insurance_intelligence.evaluation.live_certification_evidence import (
    build_governed_live_evidence,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="outputs/evaluation/mo_022g_star_copay_live.json",
        help="Local raw live-run artifact",
    )
    parser.add_argument(
        "--output",
        default="outputs/evaluation/mo_022g_star_copay_evidence.json",
        help="Governed evidence projection",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    artifact = json.loads(input_path.read_text(encoding="utf-8"))
    evidence = build_governed_live_evidence(artifact)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(evidence.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("=" * 72)
    print("MO-022G GOVERNED LIVE CERTIFICATION EVIDENCE")
    print("=" * 72)
    print(f"Evidence ID        : {evidence.evidence_id}")
    print(f"Routing decision   : {evidence.routing_decision}")
    print(f"Hard failures      : {', '.join(evidence.hard_failure_codes) or 'NONE'}")
    print(f"Reviewer decision  : {evidence.reviewer_decision}")
    print(f"Certification      : NOT GRANTED")
    print(f"Output             : {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
