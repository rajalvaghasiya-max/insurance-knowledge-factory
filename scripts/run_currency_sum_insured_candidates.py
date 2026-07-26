from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.extraction_primitives.currency_sum_insured_parser import CurrencySumInsuredParser


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract governed currency evidence candidates from one parsed PDF artifact.")
    parser.add_argument("--parse-artifact", required=True, help="Repository-relative parsed-PDF JSON artifact.")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--output-path", required=True, help="Repository-relative candidate-output JSON path.")
    args = parser.parse_args()

    root = Path(args.repository_root).resolve()
    parse_path = (root / args.parse_artifact).resolve()
    output_path = (root / args.output_path).resolve()
    try:
        parse_path.relative_to(root)
        output_path.relative_to(root)
    except ValueError as exc:
        raise SystemExit("Paths must remain within repository root.") from exc

    result = CurrencySumInsuredParser().extract_from_parsed_document(json.loads(parse_path.read_text(encoding="utf-8")))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print("=" * 70)
    print("CURRENCY / SUM-INSURED CANDIDATES")
    print("=" * 70)
    print(f"Status          : {result['status']}")
    print(f"Candidates      : {result['candidate_count']}")
    print(f"Source SHA-256  : {result['source']['sha256']}")
    print(f"Output          : {output_path}")
    print("NOTE: candidate output only; no canonical facts or publication state changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
