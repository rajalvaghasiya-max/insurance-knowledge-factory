"""Generic CLI for recording a timestamped official-source observation.

This is an operational wrapper around SourceObservationRecord. It removes the
need to hand-author an observation timestamp/spec for each product while
preserving the existing governed contract. It does not decide currentness,
identity, facts, publication, or entitlement.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from factory_core.governance.source_observation import SourceObservationRecord


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record a governed byte comparison against an official source."
    )
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--registration-path", required=True)
    parser.add_argument("--observation-id", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-page-url", required=True)
    parser.add_argument("--source-page-artifact-path", required=True)
    parser.add_argument("--observed-pdf-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--http-status", type=int, default=200)
    parser.add_argument("--content-type", default="application/pdf")
    parser.add_argument("--capture-strategy", default="manual_official_download")
    parser.add_argument("--source-issued-label")
    parser.add_argument("--effective-date-signal")
    parser.add_argument("--version-signal")
    args = parser.parse_args()

    observed_at = datetime.now(timezone.utc).isoformat()
    spec = {
        "schema_version": "1.0",
        "record_type": "source_observation_record_v1",
        "observation_id": args.observation_id,
        "registered_document": {"registration_path": args.registration_path},
        "observation": {
            "retrieval_status": "succeeded",
            "source_url": args.source_url,
            "source_url_key": args.source_url,
            "source_page_url": args.source_page_url,
            "source_page_artifact_path": args.source_page_artifact_path,
            "observed_at": observed_at,
            "capture_strategy": args.capture_strategy,
            "http_status": args.http_status,
            "content_type": args.content_type,
            "observed_pdf_path": args.observed_pdf_path,
        },
        "source_signals": {
            "source_issued_label": args.source_issued_label,
            "effective_date_signal": args.effective_date_signal,
            "version_signal": args.version_signal,
        },
    }

    builder = SourceObservationRecord()
    result = builder.build(spec=spec, repository_root=Path(args.repository_root))
    output = builder.write_output(
        result,
        repository_root=Path(args.repository_root),
        output_path=args.output_path,
    )
    record = result.record
    print("=" * 70)
    print("OFFICIAL SOURCE OBSERVATION")
    print("=" * 70)
    print(f"Output             : {output}")
    print(f"Observation        : {record['observation_id']}")
    print(f"Observed at        : {record['official_observation']['observed_at']}")
    print(f"Document version   : {record['registered_document']['document_version_id']}")
    print(f"Byte comparison    : {record['byte_comparison']['status']}")
    print("NOTE: observation only; temporal review remains required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
