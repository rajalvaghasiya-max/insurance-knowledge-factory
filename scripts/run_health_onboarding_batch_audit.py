"""CLI runner for the Phase-2A Health onboarding batch audit."""
from __future__ import annotations

import argparse
from pathlib import Path

from factory_core.governance.health_onboarding_batch_audit import HealthOnboardingBatchAudit


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a read-only Phase-2A Health onboarding batch audit.")
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--spec-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    result = HealthOnboardingBatchAudit.audit_from_spec_file(
        spec_path=Path(args.spec_path), repository_root=Path(args.repository_root)
    )
    output = HealthOnboardingBatchAudit.write_output(
        result, repository_root=Path(args.repository_root), output_path=args.output_path
    )
    summary = result.manifest["batch_summary"]
    print("=" * 70)
    print("PHASE-2A HEALTH ONBOARDING BATCH AUDIT")
    print("=" * 70)
    print(f"Output                       : {output}")
    print(f"Products                     : {result.manifest['product_count']}")
    print(f"Products with missing data   : {summary['products_with_explicit_missing_artifacts']}")
    print(f"Missing/undeclared artifacts : {summary['missing_or_undeclared_artifact_count']}")
    print(f"Review routing records       : {summary['review_routing_record_count']}")
    print(f"Risk tiers                   : {summary['review_risk_tier_counts']}")
    print(f"Product-specific code changes: {summary['product_identity_bearing_production_code_changes']}")
    print("-" * 70)
    print("PER-PRODUCT GAP DETAIL")
    print("-" * 70)
    for product in result.manifest["products"]:
        print(f"{product['entity_id']}")
        missing = product["missing_or_undeclared_artifacts"]
        if not missing:
            print("  complete for audited artifact set")
        else:
            for key in missing:
                artifact = product["artifacts"][key]
                print(f"  {key}: {artifact['status']}")
        routing = product.get("review_risk_summary")
        if routing is None:
            print("  review_risk_routing: unavailable")
        else:
            print(
                "  review_risk_routing: "
                f"{routing['routing_record_count']} record(s), tiers={routing['tier_counts']}"
            )
    print("NOTE: read-only audit; no product fact, adjudication, or publication is created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
