"""CLI for controlled amendment of one resolved reviewer-decision record."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.extraction_primitives.reviewer_decision_amendment import (
    ReviewerDecisionAmendmentWorkflow,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Amend one resolved reviewer-decision record; no submission or facts are created."
    )
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--decision-record-id", required=True)
    parser.add_argument(
        "--decision", required=True,
        choices=("accept", "reject", "split_further", "defer"),
    )
    parser.add_argument("--reviewer-identity", required=True)
    parser.add_argument("--reviewed-at", required=True)
    parser.add_argument("--review-rationale", required=True)
    parser.add_argument("--selected-role")
    parser.add_argument("--selected-benefit-scope")
    parser.add_argument("--selected-band-scope")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    if output_path.exists():
        raise SystemExit("output-path must not already exist")
    document = json.loads(input_path.read_text(encoding="utf-8"))
    output = ReviewerDecisionAmendmentWorkflow.amend_resolved_record(
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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    amended = next(
        record for record in output["decision_records"]
        if record["decision_record_id"] == args.decision_record_id
    )
    print("=" * 70)
    print("REVIEWER DECISION AMENDMENT")
    print("=" * 70)
    print(f"Status             : {output['status']}")
    print(f"Decision record    : {args.decision_record_id}")
    print(f"Amended decision   : {amended['decision']}")
    print(f"Amendment count    : {len(output.get('decision_amendment_history', []))}")
    print(f"Output             : {output_path.resolve()}")
    print("NOTE: decision amendment only; no immutable submission, canonical fact, or publication")


if __name__ == "__main__":
    main()
