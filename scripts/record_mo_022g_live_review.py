"""Record a governed human-review decision for MO-022G live evidence."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from insurance_intelligence.evaluation.live_certification_review import (
    LiveCertificationReviewerDecision,
    build_governed_live_review,
)


DEFAULT_INPUT = Path("outputs/evaluation/mo_022g_star_copay_evidence.json")
DEFAULT_OUTPUT = Path("outputs/evaluation/mo_022g_star_copay_review.json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--reviewer-id", required=True)
    parser.add_argument(
        "--decision",
        required=True,
        choices=[item.value for item in LiveCertificationReviewerDecision],
    )
    parser.add_argument("--rationale", required=True)
    parser.add_argument(
        "--reviewed-at",
        default=None,
        help="ISO-8601 timestamp; defaults to current UTC time",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    evidence = json.loads(args.input.read_text(encoding="utf-8"))
    reviewed_at = args.reviewed_at or datetime.now(timezone.utc).isoformat()
    review = build_governed_live_review(
        evidence,
        reviewer_id=args.reviewer_id,
        reviewed_at=reviewed_at,
        decision=LiveCertificationReviewerDecision(args.decision),
        rationale=args.rationale,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(review.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("=" * 72)
    print("MO-022G GOVERNED LIVE REVIEW")
    print("=" * 72)
    print(f"Evidence ID       : {review.evidence_id}")
    print(f"Review ID         : {review.review_id}")
    print(f"Decision          : {review.decision.value}")
    print(f"Reviewer          : {review.reviewer_id}")
    print(f"Output            : {args.output}")
    print("Certification     : NOT GRANTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
