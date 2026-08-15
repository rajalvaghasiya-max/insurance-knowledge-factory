"""CLI for locating parsed PDF artifacts by immutable source SHA-256."""
from __future__ import annotations

import argparse
from pathlib import Path

from factory_core.governance.parsed_artifact_locator import ParsedArtifactLocator


def main() -> int:
    parser = argparse.ArgumentParser(description="Locate retained parsed-PDF JSON artifacts by source SHA-256.")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument(
        "--search-root",
        action="append",
        dest="search_roots",
        help="Optional repository-relative root. Repeat to search multiple roots; defaults to archive and knowledge.",
    )
    args = parser.parse_args()

    result = ParsedArtifactLocator.locate(
        repository_root=Path(args.repository_root),
        source_sha256=args.source_sha256,
        search_roots=args.search_roots,
    ).manifest

    print("=" * 70)
    print("PARSED PDF ARTIFACT LOCATOR")
    print("=" * 70)
    print(f"Source SHA-256     : {result['source_sha256']}")
    print(f"Status             : {result['locator_status']}")
    print(f"JSON files scanned : {result['scanned_json_files']}")
    print(f"Matches            : {result['match_count']}")
    for item in result["matches"]:
        print(f"- {item['path']} | pages={item['page_count']} | text_pages={item['valid_text_page_count']}")
    print("NOTE: localization only; no identity, currentness, review, fact, or publication decision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
