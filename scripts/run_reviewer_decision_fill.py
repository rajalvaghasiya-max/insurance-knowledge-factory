"""Fill one pending reviewer-decision record without submitting or publishing it."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.extraction_primitives.reviewer_decision_fill import (
    ReviewerDecisionFillError,
    ReviewerDecisionFillWorkflow,
)


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json_new(path: Path, document: dict) -> None:
    if path.exists():
        raise ReviewerDecisionFillError(
            f"refusing to overwrite existing output: {path}. Choose a new output path to preserve the input artifact."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--decision-record-id", required=True)
    parser.add_argument("--decision", required=True, choices=["accept", "reject", "split_further", "defer"])
    parser.add_argument("--reviewer-identity", required=True)
    parser.add_argument("--reviewed-at", required=True, help="ISO-8601 timestamp, e.g. 2026-07-05T15:30:00+05:30")
    parser.add_argument("--review-rationale", required=True)
    parser.add_argument("--selected-role")
    parser.add_argument("--selected-benefit-scope")
    parser.add_argument("--selected-band-scope")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    if input_path.resolve() == output_path.resolve():
        parser.error("--output-path must differ from --input-path; input decision artifacts are never modified")

    try:
        document = _read_json(input_path)
        updated = ReviewerDecisionFillWorkflow.fill_pending_record(
            document,
            decision_record_id=args.decision_record_id,
            decision=args.decision,
            reviewer_identity=args.reviewer_identity,
            reviewed_at=args.reviewed_at,
            review_rationale=args.review_rationale,
            selected_role=args.selected_role,
            selected_benefit_scope=args.selected_benefit_scope,
            selected_band_scope=args.selected_band_scope,
        )
        _write_json_new(output_path, updated)
    except (OSError, json.JSONDecodeError, ReviewerDecisionFillError) as exc:
        parser.error(str(exc))

    resolved = sum(1 for record in updated["decision_records"] if record["review_status"] == "decision_recorded")
    print("=" * 70)
    print("REVIEWER DECISION FILL")
    print("=" * 70)
    print(f"Status             : {updated['status']}")
    print(f"Decision record    : {args.decision_record_id}")
    print(f"Resolved records   : {resolved}/{updated['decision_record_count']}")
    print(f"Output             : {output_path.resolve()}")
    print("NOTE: decision record only; no immutable submission, canonical fact, or publication")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
