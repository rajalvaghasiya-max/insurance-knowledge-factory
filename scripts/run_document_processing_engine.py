from __future__ import annotations

import argparse
import json

from knowledge_domains.health.processing.document_processing_engine import DocumentProcessingEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Department III — Document Processing Engine v2.0.")
    parser.add_argument("--limit", type=int, default=1, help="Maximum jobs to process from factory queue.")
    parser.add_argument("--dry-run", action="store_true", help="Process without writing outputs or updating registry.")
    parser.add_argument("--print-json", action="store_true", help="Print full JSON result.")

    args = parser.parse_args()
    engine = DocumentProcessingEngine()
    result = engine.run_from_queue(limit=args.limit, write=not args.dry_run)

    print()
    print("=" * 78)
    print("DEPARTMENT III — DOCUMENT PROCESSING ENGINE v2.0")
    print("=" * 78)
    print(f"Version     : {result['document_processing_engine_version']}")
    print(f"Jobs        : {result['job_count']}")
    print(f"Completed   : {result['completed_count']}")
    print(f"Certified   : {result['certified_count']}")
    print(f"Failed      : {result['failed_count']}")
    print("-" * 78)

    for item in result["results"]:
        if item.get("status") == "completed":
            print(
                f"[completed] [quality={item.get('quality_score')}] "
                f"[certification={item.get('certification_status')}] {item['document_id']} "
                f"sections={item['section_count']} tables={item['table_count']} "
                f"clauses={item['clause_count']} xrefs={item['cross_reference_count']}"
            )
            print(f"  asset        : {item['output_path']}")
            print(f"  manifest     : {item['manifest_path']}")
            print(f"  certification: {item['certification_report_path']}")
        else:
            print(f"[failed] {item.get('document_id')} error={item.get('error')}")

    print("=" * 78)

    if args.print_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
