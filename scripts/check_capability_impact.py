"""Reconcile a committed capability-impact declaration against repository evidence."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from capability_control import CapabilityCatalogError
from capability_control.development_protocol import (
    DevelopmentProtocolError,
    check_development_protocol,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--head-ref", default="HEAD")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = check_development_protocol(
            repo_root=Path(args.repo_root),
            base_ref=args.base_ref,
            head_ref=args.head_ref,
        )
    except (DevelopmentProtocolError, CapabilityCatalogError) as exc:
        print(f"CAPABILITY_IMPACT_INVALID: {exc}", file=sys.stderr)
        return 2

    if not report.declaration_required and report.declaration is None:
        print("CAPABILITY_IMPACT_NOT_REQUIRED")
        return 0

    if report.errors:
        for error in report.errors:
            print(f"CAPABILITY_IMPACT_FAIL {error}", file=sys.stderr)
        return 1

    declaration = report.declaration
    assert declaration is not None
    print(
        "CAPABILITY_IMPACT_OK "
        f"change_id={declaration.change_id} "
        f"classification={declaration.classification} "
        f"capabilities={','.join(declaration.capability_ids)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
