
"""CLI for P1.9A.1 publication-review decision templates and submissions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.extraction_primitives.publication_review_decision_submission import (
    PublicationReviewDecisionSubmissionContract,
)


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path: str, document: dict) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare or record non-publishing human publication-review decisions."
    )
    parser.add_argument("--packet-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--mode", choices=("template", "record"), required=True)
    parser.add_argument("--prepared-by")
    parser.add_argument("--prepared-at")
    parser.add_argument("--decision-spec-path")
    args = parser.parse_args()

    packet = _load(args.packet_path)
    if args.mode == "template":
        if not args.prepared_by or not args.prepared_at:
            parser.error("--prepared-by and --prepared-at are required in template mode")
        document = PublicationReviewDecisionSubmissionContract.build_template(
            packet_document=packet,
            prepared_by=args.prepared_by,
            prepared_at=args.prepared_at,
        )
        out = _write(args.output_path, document)
        print("=" * 70)
        print("PUBLICATION REVIEW DECISION TEMPLATE")
        print("=" * 70)
        print(f"Packet ID       : {document['source_publication_review_packet_id']}")
        print(f"Decision slots  : {document['decision_count']}")
        print(f"Output          : {out.resolve()}")
        print("NOTE: template only; edit each decision and set reviewed_by_human=true before record mode")
        return 0

    if not args.decision_spec_path:
        parser.error("--decision-spec-path is required in record mode")
    submission = PublicationReviewDecisionSubmissionContract.record(
        packet_document=packet,
        decision_spec=_load(args.decision_spec_path),
    )
    out = _write(args.output_path, submission)
    print("=" * 70)
    print("PUBLICATION REVIEW DECISION SUBMISSION")
    print("=" * 70)
    print(f"Status          : {submission['status']}")
    print(f"Submission ID   : {submission['submission_id']}")
    print(f"Decision count  : {submission['submitted_decision_count']}")
    print(f"Decision counts : {submission['decision_counts']}")
    print(f"Output          : {out.resolve()}")
    print("NOTE: no fact publication, reusable knowledge creation, or entitlement decision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
