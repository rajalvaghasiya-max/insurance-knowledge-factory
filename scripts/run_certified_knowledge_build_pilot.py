"""Generic CLI for a governed certified-knowledge build pilot."""
from __future__ import annotations
import argparse, json
from dataclasses import asdict
from pathlib import Path
from insurance_intelligence.orchestration.star_comprehensive_knowledge_build import build_star_comprehensive_copay_snapshot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-request-id", required=True)
    parser.add_argument("--product-reference", required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    if args.product_reference != "star_health:star_comprehensive" or args.topic != "conditional_copayment":
        parser.error("this pilot currently supports star_health:star_comprehensive / conditional_copayment")
    result = build_star_comprehensive_copay_snapshot(
        repository_root=Path(args.repository_root), build_request_id=args.build_request_id,
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
