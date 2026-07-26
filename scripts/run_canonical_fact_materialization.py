"""Materialize selected governed facts into an immutable unpublished artifact."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.extraction_primitives.canonical_fact_materialization import (
    CanonicalFactMaterializationContract,
)


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize selected governed facts; never publishes facts or evaluates entitlement."
    )
    parser.add_argument("--input-path", required=True, help="Governed fact-selection artifact.")
    parser.add_argument("--output-path", required=True, help="New materialization artifact path; must not already exist.")
    parser.add_argument("--materialized-by", required=True)
    parser.add_argument("--materialized-at", required=True, help="ISO-8601 timestamp, e.g. 2026-07-05T16:45:00+05:30")
    args = parser.parse_args()

    output_path = Path(args.output_path)
    if output_path.exists():
        parser.error("--output-path already exists; materialization artifacts are write-once")

    output = CanonicalFactMaterializationContract.build_materialization_document(
        _load_json(args.input_path),
        materialized_by=args.materialized_by,
        materialized_at=args.materialized_at,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    print("=" * 70)
    print("CANONICAL FACT MATERIALIZATION")
    print("=" * 70)
    print(f"Status             : {output['status']}")
    print(f"Materialization ID : {output['materialization_id']}")
    print(f"Input submission   : {output['input']['source_submission_id']}")
    print(f"Materialized facts : {output['canonical_fact_count']}")
    print(f"Deferred / blocked : {output['non_materialized_selection_record_count']}")
    print(f"Output             : {output_path.resolve()}")
    print("NOTE: immutable canonical-fact artifact only; no publication or entitlement decision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
