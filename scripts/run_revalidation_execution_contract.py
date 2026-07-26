"""Build non-publishing revalidation execution contracts."""
from __future__ import annotations

from knowledge_domains.product.identity.revalidation_execution_contract import (
    RevalidationExecutionContractBuilder,
)


def main() -> None:
    result = RevalidationExecutionContractBuilder().build()
    report = result["report"]
    print("=" * 70)
    print("REVALIDATION EXECUTION CONTRACT")
    print("=" * 70)
    print(f"Queue items scanned : {report['queue_items_scanned']}")
    print(f"Contracts created   : {report['contracts_created']}")
    print(f"Queue items skipped : {report['queue_items_skipped']}")
    print(f"Readiness counts    : {report['readiness_counts']}")
    print(f"Publication allowed : {report['publication_allowed']}")
    print(f"Registry            : {result['registry_path']}")
    print(f"Report              : {result['report_path']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
