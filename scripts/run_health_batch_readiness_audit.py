"""Run the deterministic P2 Health batch readiness audit."""
from __future__ import annotations

from knowledge_domains.health.batch.readiness_audit import HealthBatchReadinessAudit


def main() -> None:
    result = HealthBatchReadinessAudit().build()
    report = result["report"]
    counts = report["readiness_counts"]
    print("=" * 70)
    print("HEALTH BATCH READINESS AUDIT")
    print("=" * 70)
    print(f"Candidates          : {report['candidate_count']}")
    print(f"Ready for batch     : {counts['ready_for_batch']}")
    print(f"Needs identity      : {counts['needs_identity']}")
    print(f"Needs local docs    : {counts['needs_local_documents']}")
    print(f"Blocked             : {counts['blocked']}")
    print(f"Canonical fields    : {report['canonical_field_count']}")
    print(f"Report              : {result['report_path']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
