"""Run non-publishing canonical fact validation and publication eligibility assessment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.extraction_primitives.fact_publication_eligibility import (
    FactPublicationEligibilityContract,
)


def _load_json(path: str) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-path", required=True, help="Canonical fact materialization artifact.")
    parser.add_argument("--identity-overlay-path", required=True, help="Reviewed document identity resolution overlay.")
    parser.add_argument("--output-path", required=True, help="New eligibility artifact path; must not already exist.")
    parser.add_argument("--validated-by", required=True)
    parser.add_argument("--validated-at", required=True, help="ISO-8601 timestamp.")
    args = parser.parse_args()

    output_path = Path(args.output_path)
    if output_path.exists():
        parser.error("--output-path already exists; eligibility artifacts are write-once")
    output = FactPublicationEligibilityContract.build_eligibility_document(
        _load_json(args.input_path),
        _load_json(args.identity_overlay_path),
        validated_by=args.validated_by,
        validated_at=args.validated_at,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    print("=" * 70)
    print("FACT PUBLICATION ELIGIBILITY")
    print("=" * 70)
    print(f"Status                         : {output['status']}")
    print(f"Eligibility assessment ID      : {output['eligibility_assessment_id']}")
    print(f"Input materialization          : {output['input']['materialization_id']}")
    print(f"Eligible for publication review: {output['eligible_for_publication_review_count']}")
    print(f"Blocked                        : {output['blocked_count']}")
    print(f"Deferred                       : {output['deferred_count']}")
    print(f"Output                         : {output_path.resolve()}")
    print("NOTE: assessment only; no publication, currentness upgrade, or entitlement decision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
