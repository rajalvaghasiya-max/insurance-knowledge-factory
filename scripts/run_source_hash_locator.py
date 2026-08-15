"""CLI runner for generic repository-local source localization by SHA-256."""
from __future__ import annotations

import argparse
from pathlib import Path

from factory_core.governance.source_hash_locator import SourceHashLocator


def main() -> int:
    parser = argparse.ArgumentParser(description="Locate retained repository sources by immutable SHA-256.")
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--sha256", action="append", required=True, dest="sha256_values")
    parser.add_argument("--search-root", action="append", dest="search_roots")
    args = parser.parse_args()

    matches = SourceHashLocator.locate(
        repository_root=Path(args.repository_root),
        sha256_values=args.sha256_values,
        search_roots=args.search_roots,
    )
    print("=" * 70)
    print("SOURCE HASH LOCATOR")
    print("=" * 70)
    for digest, rows in matches.items():
        print(digest)
        if not rows:
            print("  NOT FOUND")
        else:
            for row in rows:
                print(f"  {row.relative_path} ({row.size_bytes} bytes)")
    print("NOTE: localization only; no identity/currentness/fact/publication decision is created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
