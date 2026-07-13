"""CLI for P2.5-C read-only legacy conditional-rule projection."""

from __future__ import annotations

import argparse
from pathlib import Path

from factory_core.canonical.legacy_conditional_rule_adapter import (
    CanonicalProductContext,
    LegacyConditionalRuleAdapter,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Project one authoritative conditional-rule artifact into Canonical Model v1."
    )
    parser.add_argument("--rules-path", required=True)
    parser.add_argument("--publication-receipt-path", required=True)
    parser.add_argument("--lineage-manifest-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--insurer-id", required=True)
    parser.add_argument("--insurer-legal-name", required=True)
    parser.add_argument("--insurer-type", default=None)
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--product-name", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--product-version-id", required=True)
    parser.add_argument("--product-version-label", default=None)
    parser.add_argument("--product-uin", default=None)
    parser.add_argument("--product-family-name", default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    context = CanonicalProductContext(
        insurer_id=args.insurer_id,
        insurer_legal_name=args.insurer_legal_name,
        insurer_type=args.insurer_type,
        product_id=args.product_id,
        product_name=args.product_name,
        domain=args.domain,
        product_version_id=args.product_version_id,
        product_version_label=args.product_version_label,
        product_uin=args.product_uin,
        product_family_name=args.product_family_name,
    )
    adapter = LegacyConditionalRuleAdapter()
    projection = adapter.project_from_files(
        rules_path=args.rules_path,
        publication_receipt_path=args.publication_receipt_path,
        lineage_manifest_path=args.lineage_manifest_path,
        context=context,
    )
    output = adapter.write_projection(projection, args.output_path)
    counts = projection.report["mapping_counts"]
    print("=" * 70)
    print("CANONICAL LEGACY CONDITIONAL-RULE PROJECTION")
    print("=" * 70)
    print(f"Projection status      : {projection.report['projection_status']}")
    print(f"Canonical assertions   : {counts['canonical_assertions']}")
    print(f"Evidence spans         : {counts['canonical_evidence_spans']}")
    print(f"Document versions      : {counts['canonical_document_versions']}")
    print(f"Output                 : {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
