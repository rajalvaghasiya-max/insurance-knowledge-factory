"""Run P2.5-E controlled canonical projection pilot."""
from __future__ import annotations

import argparse
from pathlib import Path

from factory_core.canonical.canonical_projection_pilot import CanonicalProjectionPilot


def main() -> int:
    parser = argparse.ArgumentParser(description="Run canonical projection pilot from an explicit spec.")
    parser.add_argument("--spec-path", required=True)
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--report-path", required=True)
    args = parser.parse_args()

    root = Path(args.repository_root)
    result = CanonicalProjectionPilot().run_from_spec_file(
        spec_path=args.spec_path,
        repository_root=root,
    )
    report = CanonicalProjectionPilot().write_report(result, args.report_path)
    print("=" * 70)
    print("CANONICAL PROJECTION PILOT")
    print("=" * 70)
    print(f"Pilot status          : {result.report['pilot_status']}")
    print(f"Canonical assertions  : {result.report['mapping_counts']['canonical_assertions']}")
    print(f"Evidence spans        : {result.report['mapping_counts']['canonical_evidence_spans']}")
    print(f"Projection output     : {result.report['output_path']}")
    print(f"Pilot report          : {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
