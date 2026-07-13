"""CLI runner for P1.5d-0 governed source observation records."""
from __future__ import annotations

import argparse
from pathlib import Path

from factory_core.governance.source_observation import SourceObservationRecord


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a non-mutating governed source observation record."
    )
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--spec-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    builder = SourceObservationRecord()
    result = builder.build_from_spec_file(
        spec_path=Path(args.spec_path),
        repository_root=Path(args.repository_root),
    )
    output = builder.write_output(
        result,
        repository_root=Path(args.repository_root),
        output_path=args.output_path,
    )
    record = result.record
    print("=" * 70)
    print("GOVERNED SOURCE OBSERVATION RECORD")
    print("=" * 70)
    print(f"Output             : {output}")
    print(f"Observation        : {record['observation_id']}")
    print(f"Document version   : {record['registered_document']['document_version_id']}")
    print(f"Retrieval          : {record['official_observation']['retrieval_status']}")
    print(f"Byte comparison    : {record['byte_comparison']['status']}")
    print("Temporal review    : required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
