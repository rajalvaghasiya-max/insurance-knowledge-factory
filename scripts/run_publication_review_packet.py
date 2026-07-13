"""CLI runner for P1.9A publication-review packets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.extraction_primitives.publication_review_packet import PublicationReviewPacketContract


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a non-publishing human review packet for eligible canonical facts.")
    parser.add_argument("--materialization-path", required=True)
    parser.add_argument("--eligibility-path", required=True)
    parser.add_argument("--reviewer-submission-path", required=True)
    parser.add_argument("--candidate-review-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--prepared-by", required=True)
    parser.add_argument("--prepared-at", required=True)
    args = parser.parse_args()
    packet = PublicationReviewPacketContract.build_packet(
        materialization_document=_load(args.materialization_path),
        eligibility_document=_load(args.eligibility_path),
        reviewer_submission_document=_load(args.reviewer_submission_path),
        candidate_review_document=_load(args.candidate_review_path),
        prepared_by=args.prepared_by,
        prepared_at=args.prepared_at,
    )
    out = Path(args.output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("=" * 70)
    print("PUBLICATION REVIEW PACKET")
    print("=" * 70)
    print(f"Status      : {packet['status']}")
    print(f"Packet ID   : {packet['publication_review_packet_id']}")
    print(f"Input facts : {packet['input']['eligible_canonical_fact_count']}")
    print(f"Packet items: {packet['packet_item_count']}")
    print(f"Output      : {out.resolve()}")
    print("NOTE: packet only; no approval, publication, reusable knowledge, or entitlement decision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
