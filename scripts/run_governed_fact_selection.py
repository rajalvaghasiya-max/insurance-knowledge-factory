"""Build an unpublished governed fact-selection artifact from a review submission."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.extraction_primitives.governed_fact_selection import GovernedFactSelectionContract


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Select governed facts from an immutable review submission; never publishes facts.")
    parser.add_argument("--input-path", required=True, help="Immutable submitted human-review artifact.")
    parser.add_argument("--output-path", required=True, help="New selection artifact path; must not already exist.")
    parser.add_argument("--selector-identity", required=True)
    parser.add_argument("--selected-at", required=True, help="ISO-8601 timestamp, e.g. 2026-07-05T16:30:00+05:30")
    args = parser.parse_args()

    output_path = Path(args.output_path)
    if output_path.exists():
        parser.error("--output-path already exists; selection artifacts are write-once")

    output = GovernedFactSelectionContract.build_selection_document(
        _load_json(args.input_path),
        selector_identity=args.selector_identity,
        selected_at=args.selected_at,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    counts: dict[str, int] = {}
    for record in output["selection_records"]:
        counts[record["selection_status"]] = counts.get(record["selection_status"], 0) + 1
    print("=" * 70)
    print("GOVERNED FACT SELECTION")
    print("=" * 70)
    print(f"Status             : {output['status']}")
    print(f"Input submission   : {output['input']['submission_id']}")
    print(f"Selection records  : {output['selection_record_count']}")
    print(f"Selected           : {counts.get('selected_governed_fact', 0)}")
    print(f"Deferred           : {counts.get('deferred', 0)}")
    print(f"Blocked            : {counts.get('blocked', 0)}")
    print(f"Output             : {output_path.resolve()}")
    print("NOTE: selection artifact only; no fact-store write, publication, or entitlement decision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
