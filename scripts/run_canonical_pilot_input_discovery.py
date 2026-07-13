"""Run read-only candidate discovery for a canonical projection pilot."""
from __future__ import annotations

import argparse
from pathlib import Path

from factory_core.canonical.canonical_pilot_input_discovery import CanonicalPilotInputDiscovery


def main() -> int:
    parser = argparse.ArgumentParser(description="Locate review candidates for a canonical projection pilot.")
    parser.add_argument("--entity-id", required=True)
    parser.add_argument("--field", required=True)
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--report-path", required=True)
    args = parser.parse_args()

    discovery = CanonicalPilotInputDiscovery()
    result = discovery.discover(
        repository_root=Path(args.repository_root),
        entity_id=args.entity_id,
        field=args.field,
    )
    report_path = discovery.write_report(result, args.report_path)
    print("=" * 70)
    print("CANONICAL PILOT INPUT DISCOVERY")
    print("=" * 70)
    print(f"Authoritative rule candidates : {len(result.report['authoritative_rule_artifact_candidates'])}")
    print(f"Document reference candidates : {len(result.report['document_reference_candidates'])}")
    print(f"Extraction reference candidates: {len(result.report['extraction_reference_candidates'])}")
    print(f"Report                        : {report_path}")
    print("Selection made                : False (human review required)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
