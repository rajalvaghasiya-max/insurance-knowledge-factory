from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.customer_document_intelligence import (
    DeductibleCustomerFactSelector,
)
from knowledge_domains.health.extraction_primitives.currency_sum_insured_parser import (
    CurrencySumInsuredParser,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract a governed customer-specific deductible fact from a "
            "parsed Health customer document."
        )
    )
    parser.add_argument("--parsed-document", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    parsed_path = Path(args.parsed_document)
    output_path = Path(args.output)

    parsed_document = json.loads(parsed_path.read_text(encoding="utf-8"))
    candidates = CurrencySumInsuredParser().extract_from_parsed_document(
        parsed_document
    )
    fact = DeductibleCustomerFactSelector().select(candidates)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(fact, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )

    print("=" * 72)
    print("CUSTOMER DEDUCTIBLE FACT")
    print("=" * 72)
    print(f"Input        : {parsed_path}")
    print(f"Output       : {output_path}")
    print(f"Fact ID      : {fact['fact_id']}")
    print(f"Status       : {fact['status']}")
    print(f"Candidate(s) : {fact['candidate_count']}")


if __name__ == "__main__":
    main()
