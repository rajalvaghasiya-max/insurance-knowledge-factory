"""Run the P1.5b read-only governed identity readiness audit."""
from __future__ import annotations

import argparse
from pathlib import Path

from knowledge_domains.health.batch.governed_identity_readiness_audit import (
    GovernedIdentityReadinessAudit,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a read-only governed product identity readiness report."
    )
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--scope-path",
        default="registry/p1_5b_governed_identity_readiness_scope.json",
    )
    parser.add_argument(
        "--report-path",
        default="reports/p1_5b_governed_identity_readiness_report.json",
    )
    args = parser.parse_args()

    result = GovernedIdentityReadinessAudit(
        base_dir=Path(args.repository_root),
        scope_path=args.scope_path,
        report_path=args.report_path,
    ).build()
    report = result["report"]
    counts = report["governed_readiness_counts"]

    print("=" * 70)
    print("GOVERNED IDENTITY READINESS AUDIT")
    print("=" * 70)
    print(f"Scope             : {report['scope_name']}")
    print(f"Products          : {report['product_count']}")
    print(f"Current ready     : {counts['governed_current_entitlement_ready']}")
    print(f"Review ready      : {counts['governed_evidence_review_ready_current_entitlement_blocked']}")
    print(f"Legacy migration  : {counts['legacy_governance_migration_required']}")
    print(f"Incomplete        : {counts['governance_incomplete']}")
    print(f"Report            : {result['report_path']}")
    print("=" * 70)
    for item in report["products"]:
        print(f"- {item['entity_id']} | {item['governed_readiness_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
