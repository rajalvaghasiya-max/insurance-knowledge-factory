"""CLI runner for P1.8 document currentness evidence records."""
from __future__ import annotations

import argparse
from pathlib import Path

from factory_core.governance.document_currentness_evidence import (
    DocumentCurrentnessEvidenceRecord,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build an immutable evidence-only document currentness record."
    )
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--spec-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    policy = DocumentCurrentnessEvidenceRecord()
    result = policy.build_from_spec_file(
        spec_path=Path(args.spec_path),
        repository_root=Path(args.repository_root),
    )
    output = policy.write_output(
        result,
        repository_root=Path(args.repository_root),
        output_path=args.output_path,
    )
    record = result.record
    print("=" * 70)
    print("DOCUMENT CURRENTNESS EVIDENCE")
    print("=" * 70)
    print(f"Output               : {output}")
    print(f"Registered version   : {record['registered_document']['document_version_id']}")
    print(f"Observation          : {record['source_observation']['observation_id']}")
    print(f"Evidence conclusion  : {record['currentness_evidence_conclusion']}")
    print(f"Positive evidence    : {record['positive_currentness_evidence_count']}")
    print("NOTE: evidence only; no temporal decision, publication, or entitlement decision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
