"""Search the verified capability catalog before proposing a material capability."""
from __future__ import annotations

import argparse
from pathlib import Path

from capability_control.catalog import load_catalog
from capability_control.preflight import preflight_capability

DEFAULT_CATALOG = "governance/capabilities/catalog.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--catalog", default=DEFAULT_CATALOG)
    parser.add_argument("--limit", type=int, default=8)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.repo_root).resolve()
    catalog_path = Path(args.catalog)
    if not catalog_path.is_absolute():
        catalog_path = root / catalog_path
    catalog = load_catalog(catalog_path)
    result = preflight_capability(catalog=catalog, query=args.query, limit=args.limit)

    print(f"query={result.query}")
    print(f"classification={result.classification}")
    print("new_authorized=false")
    for candidate in result.candidates:
        terms = ",".join(candidate.matched_terms)
        print(
            f"{candidate.score:.4f} {candidate.capability_id} "
            f"lifecycle={candidate.lifecycle_status} reuse={candidate.reuse_policy} "
            f"matched={terms}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
