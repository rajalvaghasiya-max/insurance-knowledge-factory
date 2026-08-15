"""CLI runner for generic governed review-risk routing."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from factory_core.governance.review_risk_routing import ReviewRiskRoutingContract


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assign transparent review-risk tiers without adjudicating evidence."
    )
    parser.add_argument("--review-document", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    review_path = Path(args.review_document)
    payload = json.loads(review_path.read_text(encoding="utf-8"))
    result = ReviewRiskRoutingContract.route(payload).manifest

    output = Path(args.output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    counts = result["workload_summary"]["tier_counts"]
    print("=" * 70)
    print("GOVERNED REVIEW RISK ROUTING")
    print("=" * 70)
    print(f"Output    : {output}")
    print(f"Groups    : {result['routing_record_count']}")
    print(f"Critical  : {counts['critical']}")
    print(f"High      : {counts['high']}")
    print(f"Medium    : {counts['medium']}")
    print(f"Low       : {counts['low']}")
    print("Adjudication: none")
    print("Publication : none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
