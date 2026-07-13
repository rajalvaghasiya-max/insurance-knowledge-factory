"""Create pending human-review decision records from currency review groups."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.extraction_primitives.reviewer_decision_record import ReviewerDecisionRecordContract


def main() -> int:
    parser = argparse.ArgumentParser(description="Create reviewer decision-record templates; no facts are created.")
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()
    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    review_document = json.loads(input_path.read_text(encoding="utf-8"))
    decision_document = ReviewerDecisionRecordContract.build_pending_document(review_document)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(decision_document, indent=2) + "\n", encoding="utf-8")
    print("=" * 70)
    print("REVIEWER DECISION RECORD TEMPLATE")
    print("=" * 70)
    print(f"Status             : {decision_document['status']}")
    print(f"Input review groups: {decision_document['input']['input_review_group_count']}")
    print(f"Decision records   : {decision_document['decision_record_count']}")
    print(f"Output             : {output_path.resolve()}")
    print("NOTE: pending human-review records only; no canonical facts or publication")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
