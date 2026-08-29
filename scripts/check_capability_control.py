"""Validate PolicyScna capability memory against repository-derived structure."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from capability_control import CapabilityCatalogError, load_catalog, scan_repository

DEFAULT_CATALOG = "governance/capabilities/catalog.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--catalog", default=DEFAULT_CATALOG)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    catalog_path = Path(args.catalog)
    if not catalog_path.is_absolute():
        catalog_path = repo_root / catalog_path

    try:
        catalog = load_catalog(catalog_path)
        report = scan_repository(repo_root=repo_root, catalog=catalog)
    except CapabilityCatalogError as exc:
        print(f"CAPABILITY_CONTROL_INVALID: {exc}", file=sys.stderr)
        return 2

    print(f"catalog_version={catalog.catalog_version}")
    print(f"enforcement_mode={catalog.enforcement_mode}")
    print(f"registered_capabilities={len(catalog.capabilities)}")
    print(f"governed_roots={len(catalog.governed_roots)}")
    print(f"unclaimed_governed_files={len(report.unclaimed_governed_files)}")

    for path in report.unclaimed_governed_files:
        print(f"UNCLAIMED_CANDIDATE {path}")
    for path in report.missing_governed_roots:
        print(f"MISSING_GOVERNED_ROOT {path}", file=sys.stderr)
    for path in report.missing_ownership_paths:
        print(f"MISSING_OWNERSHIP_PATH {path}", file=sys.stderr)
    for path in report.stale_ownership_paths:
        print(f"STALE_OWNERSHIP_PATH {path}", file=sys.stderr)

    if not report.passes_enforcement:
        print(
            "CAPABILITY_CONTROL_FAIL " + ",".join(report.strict_failure_reasons),
            file=sys.stderr,
        )
        return 1

    if report.structural_drift_detected:
        print("CAPABILITY_CONTROL_RECONCILIATION_DRIFT")
    else:
        print("CAPABILITY_CONTROL_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
