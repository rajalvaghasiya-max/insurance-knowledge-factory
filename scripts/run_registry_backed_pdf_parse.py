from __future__ import annotations

import argparse

from knowledge_domains.health.batch.registry_backed_pdf_parser import RegistryBackedPdfParser


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse registry-backed product PDFs without copying raw evidence.")
    parser.add_argument("--entity-id", default="bajaj_allianz_general:my_health_care")
    parser.add_argument("--force", action="store_true", help="Reparse even when a matching parser-version artifact already exists.")
    args = parser.parse_args()

    result = RegistryBackedPdfParser().build(entity_id=args.entity_id, force=args.force)
    report = result["report"]
    counts = report["status_counts"]
    print("=" * 70)
    print("REGISTRY-BACKED PDF PARSING")
    print("=" * 70)
    print(f"Entity                  : {report['entity_id']}")
    print(f"Intake records selected : {report['intake_records_selected']}")
    print(f"Parsed                  : {counts['parsed']}")
    print(f"Reused                  : {counts['reused']}")
    print(f"Integrity mismatches    : {counts['blocked_integrity_mismatch']}")
    print(f"Missing archive files   : {counts['blocked_missing_archive_file']}")
    print(f"Failed                  : {counts['failed']}")
    print(f"Registry                : {result['registry_path']}")
    print(f"Report                  : {result['report_path']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
