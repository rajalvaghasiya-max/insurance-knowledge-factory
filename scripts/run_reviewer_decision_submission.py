"""Validate completed reviewer decisions and emit an immutable submission artifact."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.extraction_primitives.reviewer_decision_submission import ReviewerDecisionSubmissionContract


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit completed reviewer decisions; no facts are created.")
    parser.add_argument("--input-path", required=True, help="Completed D-2 decision document.")
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--submitted-by", required=True)
    parser.add_argument("--submitted-at", required=True, help="ISO-8601 timestamp, e.g. 2026-07-05T12:00:00Z")
    parser.add_argument("--previous-submission-path", help="Optional prior immutable submission for revision linking.")
    args = parser.parse_args()

    completed = _load_json(args.input_path)
    previous = _load_json(args.previous_submission_path) if args.previous_submission_path else None
    output = ReviewerDecisionSubmissionContract.build_submission_document(
        completed,
        submitted_by=args.submitted_by,
        submitted_at=args.submitted_at,
        previous_submission_document=previous,
    )
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print("=" * 70)
    print("REVIEWER DECISION SUBMISSION")
    print("=" * 70)
    print(f"Status             : {output['status']}")
    print(f"Submitted records  : {output['submitted_record_count']}")
    print(f"Submission ID      : {output['submission_id']}")
    print(f"Output             : {output_path.resolve()}")
    print("NOTE: immutable review submission only; no canonical facts or publication")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
