"""Run a read-only repeatability-target qualification audit."""
from __future__ import annotations

import argparse
from pathlib import Path

from knowledge_domains.health.batch.target_qualification_audit import TargetQualificationAudit


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit retained policy wordings for governed repeatability-target qualification.")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--insurer-id", default="bajaj_allianz_general")
    parser.add_argument("--registry-path", default="registry/pdf_registry.json")
    parser.add_argument("--report-path", default="reports/bajaj_policy_wording_target_qualification_audit_v1.json")
    args = parser.parse_args()
    result = TargetQualificationAudit(
        base_dir=Path(args.repository_root), insurer_id=args.insurer_id,
        registry_path=args.registry_path, report_path=args.report_path,
    ).build()
    report = result["report"]
    counts = report["qualification_counts"]
    print("=" * 70)
    print("REPEATABILITY TARGET QUALIFICATION AUDIT")
    print("=" * 70)
    print(f"Insurer                 : {report['insurer_id']}")
    print(f"Policy wordings audited : {report['candidate_count']}")
    print(f"Qualified               : {counts['qualified_for_repeatability_proof']}")
    print(f"Evidence only           : {counts['evidence_only_not_qualified']}")
    print(f"Variant mismatch        : {counts['excluded_variant_mismatch']}")
    print(f"Missing provenance      : {counts['missing_provenance']}")
    print(f"Report                  : {result['report_path']}")
    print("=" * 70)
    for row in report["candidates"]:
        print(f"- {row['qualification_status']} | {row['source_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
