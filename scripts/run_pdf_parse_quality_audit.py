"""Run the PDF parse quality audit for one registered product entity."""
from __future__ import annotations

import argparse

from knowledge_domains.health.batch.pdf_parse_quality_audit import PdfParseQualityAudit


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit registry-backed PDF parse quality.")
    parser.add_argument("--entity-id", required=True, help="Registered product entity ID.")
    args = parser.parse_args()

    result = PdfParseQualityAudit().build(entity_id=args.entity_id)
    report = result["report"]
    counts = report["status_counts"]

    print("=" * 70)
    print("PDF PARSE QUALITY AUDIT")
    print("=" * 70)
    print(f"Entity                    : {args.entity_id}")
    print(f"Parse records selected    : {report['parse_records_selected']}")
    print(f"Ready for extraction      : {counts['ready_for_extraction']}")
    print(f"Needs review              : {counts['needs_review']}")
    print(f"Blocked                   : {counts['blocked']}")
    print(f"Registry                  : {result['registry_path']}")
    print(f"Report                    : {result['report_path']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
