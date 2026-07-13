"""CLI for P1.9C governed reusable product-knowledge records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.extraction_primitives.governed_reusable_product_knowledge_records import (
    GovernedReusableProductKnowledgeRecordContract,
)


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Create non-publishing governed reusable product-knowledge records from approved content-reviewed packages.")
    parser.add_argument("--package-templates-path", required=True)
    parser.add_argument("--content-review-submission-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--created-by", required=True)
    parser.add_argument("--created-at", required=True)
    args = parser.parse_args()

    document = GovernedReusableProductKnowledgeRecordContract.create_records(
        package_templates=_load(args.package_templates_path),
        content_review_submission=_load(args.content_review_submission_path),
        created_by=args.created_by,
        created_at=args.created_at,
    )
    out = Path(args.output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("=" * 70)
    print("GOVERNED REUSABLE PRODUCT KNOWLEDGE RECORDS")
    print("=" * 70)
    print(f"Status     : {document['status']}")
    print(f"Document ID: {document['record_document_id']}")
    print(f"Records    : {document['record_count']}")
    print(f"Output     : {out.resolve()}")
    print("NOTE: reusable product knowledge only; no publication, entitlement, claim decision, recommendation, or customer answer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
