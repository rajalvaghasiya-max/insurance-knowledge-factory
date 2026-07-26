"""Generate reviewer-ready records from a currency candidate document."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.extraction_primitives.currency_candidate_review import CurrencyCandidateReview


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate reviewer-ready currency evidence records.")
    parser.add_argument("--input-path", required=True, help="Shared extraction-candidate JSON document.")
    parser.add_argument("--output-path", required=True, help="Output review-record JSON path.")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    document = json.loads(input_path.read_text(encoding="utf-8"))
    result = CurrencyCandidateReview().review(document)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("=" * 70)
    print("CURRENCY CANDIDATE REVIEW")
    print("=" * 70)
    print(f"Status             : {result['status']}")
    print(f"Input candidates   : {result['input']['input_candidate_count']}")
    print(f"Review groups      : {result['review_group_count']}")
    print(f"Output             : {output_path.resolve()}")
    print("NOTE: reviewer-ready evidence records only; no canonical facts or publication")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
