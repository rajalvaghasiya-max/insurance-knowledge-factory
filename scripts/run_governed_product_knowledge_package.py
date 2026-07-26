"""CLI for P1.9B governed product-knowledge package templates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.extraction_primitives.governed_product_knowledge_package import (
    GovernedProductKnowledgePackageContract,
)


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare non-publishing governed product-knowledge package templates from approved publication-review decisions.")
    parser.add_argument("--packet-path", required=True)
    parser.add_argument("--decision-submission-path", required=True)
    parser.add_argument("--package-spec-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--prepared-by", required=True)
    parser.add_argument("--prepared-at", required=True)
    args = parser.parse_args()

    document = GovernedProductKnowledgePackageContract.build_template(
        publication_review_packet=_load(args.packet_path),
        publication_decision_submission=_load(args.decision_submission_path),
        package_spec=_load(args.package_spec_path),
        prepared_by=args.prepared_by,
        prepared_at=args.prepared_at,
    )
    out = Path(args.output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("=" * 70)
    print("GOVERNED PRODUCT KNOWLEDGE PACKAGE TEMPLATES")
    print("=" * 70)
    print(f"Status        : {document['status']}")
    print(f"Template ID   : {document['template_document_id']}")
    print(f"Approved facts: {document['approved_packet_item_count']}")
    print(f"Packages      : {document['package_count']}")
    print(f"Output        : {out.resolve()}")
    print("NOTE: templates only; no reusable knowledge, publication, entitlement, or customer answer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
