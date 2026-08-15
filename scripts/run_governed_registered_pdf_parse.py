from __future__ import annotations

import argparse
from pathlib import Path

from factory_core.governance.governed_registered_pdf_parser import GovernedRegisteredPdfParser


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse one governed registered PDF after archive-path and SHA-256 verification."
    )
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--registration-path", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--entity-id", required=True)
    parser.add_argument("--insurer-id", required=True)
    parser.add_argument("--output-path")
    args = parser.parse_args()

    result = GovernedRegisteredPdfParser(repository_root=Path(args.repository_root)).parse(
        registration_path=args.registration_path,
        source_url=args.source_url,
        entity_id=args.entity_id,
        insurer_id=args.insurer_id,
        output_path=args.output_path,
    )
    print("=" * 70)
    print("GOVERNED REGISTERED PDF PARSE")
    print("=" * 70)
    print(f"Status             : {result['status']}")
    print(f"Source SHA-256     : {result['source_sha256']}")
    print(f"Pages              : {result['page_count']}")
    print(f"Pages with text    : {result['text_page_count']}")
    print(f"Output             : {result['output_path']}")
    print("NOTE: parsed evidence only; no identity, currentness, fact, review, or publication decision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
