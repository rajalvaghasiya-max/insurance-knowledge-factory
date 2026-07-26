from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.customer_document_intelligence.concept_understanding_matcher import (
    ConceptUnderstandingMatcher,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Match a governed customer deductible fact to a certified Understanding Asset."
    )
    parser.add_argument("--customer-fact", required=True)
    parser.add_argument("--understanding-asset", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    fact_path = Path(args.customer_fact)
    asset_path = Path(args.understanding_asset)
    output_path = Path(args.output)

    customer_fact = json.loads(fact_path.read_text(encoding="utf-8"))
    result = ConceptUnderstandingMatcher().match_from_path(
        customer_fact=customer_fact,
        understanding_asset_path=asset_path,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )

    print("=" * 72)
    print("CUSTOMER FACT → UNDERSTANDING ASSET MATCH")
    print("=" * 72)
    print(f"Customer Fact       : {fact_path}")
    print(f"Understanding Asset : {asset_path}")
    print(f"Output              : {output_path}")
    print(f"Match ID            : {result['match_id']}")
    print(f"Status              : {result['status']}")


if __name__ == "__main__":
    main()
