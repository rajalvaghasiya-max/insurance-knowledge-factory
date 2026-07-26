"""Materialize or update durable document-revalidation work items."""
from __future__ import annotations

import argparse

from knowledge_domains.product.identity.revalidation_work_queue import RevalidationWorkQueue


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or update the revalidation work queue.")
    parser.add_argument("--set-status", nargs=2, metavar=("WORK_ITEM_ID", "STATUS"), help="Update an existing work item's status.")
    parser.add_argument("--note", help="Optional audit note used with --set-status.")
    args = parser.parse_args()

    queue = RevalidationWorkQueue()
    if args.set_status:
        work_item_id, status = args.set_status
        item = queue.update_status(work_item_id=work_item_id, status=status, note=args.note)
        print("=" * 70)
        print("REVALIDATION WORK QUEUE")
        print("=" * 70)
        print(f"Work item : {item['revalidation_work_item_id']}")
        print(f"Status    : {item['status']}")
        print(f"Registry  : {queue.queue_registry_path}")
        print("=" * 70)
        return

    result = queue.build()
    report = result["report"]
    print("=" * 70)
    print("REVALIDATION WORK QUEUE")
    print("=" * 70)
    print(f"Candidates scanned : {report['impact_candidates_scanned']}")
    print(f"Work items created : {report['work_items_created']}")
    print(f"Work items retained: {report['work_items_retained']}")
    print(f"Queue size         : {report['work_item_count']}")
    print(f"Status counts      : {report['status_counts']}")
    print(f"Registry           : {result['registry_path']}")
    print(f"Report             : {result['report_path']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
