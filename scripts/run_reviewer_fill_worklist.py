"""Generate a read-only reviewer-fill worklist from pending decision records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.extraction_primitives.reviewer_fill_workflow import ReviewerFillWorkflow


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate reviewer guidance; no decisions or facts are created.")
    parser.add_argument("--input-path", required=True, help="Pending D-2 reviewer decision document.")
    parser.add_argument("--output-path", required=True, help="Reviewer worklist JSON output path.")
    args = parser.parse_args()

    pending = json.loads(Path(args.input_path).read_text(encoding="utf-8"))
    output = ReviewerFillWorkflow.build_worklist_document(pending)
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print("=" * 70)
    print("REVIEWER FILL WORKLIST")
    print("=" * 70)
    print(f"Status             : {output['status']}")
    print(f"Input records      : {output['input']['input_decision_record_count']}")
    print(f"Work items         : {output['work_item_count']}")
    print(f"Output             : {output_path.resolve()}")
    print("NOTE: reviewer guidance only; no decision records, facts, or publication changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
