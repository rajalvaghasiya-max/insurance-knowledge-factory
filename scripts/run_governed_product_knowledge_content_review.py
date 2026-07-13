"""CLI for P1.9B.1 governed product-knowledge content review."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.extraction_primitives.governed_product_knowledge_content_review import (
    GovernedProductKnowledgeContentReviewContract,
)


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare or record non-publishing governed product-knowledge content review.")
    parser.add_argument("--mode", required=True, choices=["template", "record"])
    parser.add_argument("--package-templates-path", required=True)
    parser.add_argument("--content-review-template-path")
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--prepared-by")
    parser.add_argument("--prepared-at")
    parser.add_argument("--submitted-by")
    parser.add_argument("--submitted-at")
    args = parser.parse_args()

    if args.mode == "template":
        if not args.prepared_by or not args.prepared_at:
            parser.error("template mode requires --prepared-by and --prepared-at")
        document = GovernedProductKnowledgeContentReviewContract.build_review_template(
            package_templates=_load(args.package_templates_path),
            prepared_by=args.prepared_by,
            prepared_at=args.prepared_at,
        )
        status_label = "CONTENT REVIEW TEMPLATE"
        id_label = "Template ID"
        id_value = document["content_review_template_id"]
        count_label = "Review items"
        count_value = document["package_count"]
    else:
        if not args.content_review_template_path:
            parser.error("record mode requires --content-review-template-path")
        if not args.submitted_by or not args.submitted_at:
            parser.error("record mode requires --submitted-by and --submitted-at")
        document = GovernedProductKnowledgeContentReviewContract.record_review_submission(
            package_templates=_load(args.package_templates_path),
            content_review_template=_load(args.content_review_template_path),
            submitted_by=args.submitted_by,
            submitted_at=args.submitted_at,
        )
        status_label = "CONTENT REVIEW SUBMISSION"
        id_label = "Submission ID"
        id_value = document["content_review_submission_id"]
        count_label = "Decisions"
        count_value = document["submitted_decision_count"]

    out = Path(args.output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("=" * 70)
    print(status_label)
    print("=" * 70)
    print(f"Status        : {document['status']}")
    print(f"{id_label:<14}: {id_value}")
    print(f"{count_label:<14}: {count_value}")
    if "decision_counts" in document:
        print(f"Decision count: {document['decision_counts']}")
    print(f"Output        : {out.resolve()}")
    print("NOTE: review only; no reusable knowledge, publication, entitlement, or customer answer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
