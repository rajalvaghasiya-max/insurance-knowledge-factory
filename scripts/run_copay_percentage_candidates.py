"""CLI for the deterministic co-pay percentage evidence primitive."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from knowledge_domains.health.extraction_primitives.copay_percentage_parser import CopayPercentageParser

def main() -> int:
    parser = argparse.ArgumentParser(description="Emit co-pay percentage evidence candidates from a parsed PDF artifact.")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--parse-artifact", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    parse_path = Path(args.parse_artifact)
    if not parse_path.is_absolute(): parse_path = root / parse_path
    output_path = Path(args.output_path)
    if not output_path.is_absolute(): output_path = root / output_path
    result = CopayPercentageParser().extract_from_parsed_document(json.loads(parse_path.read_text(encoding="utf-8")))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("=" * 70)
    print("CO-PAY PERCENTAGE CANDIDATES")
    print("=" * 70)
    print(f"Status          : {result['status']}")
    print(f"Candidates      : {result['candidate_count']}")
    print(f"Source SHA-256  : {result['source']['sha256']}")
    print(f"Output          : {output_path}")
    print("NOTE: candidate output only; no canonical facts or publication state changed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
