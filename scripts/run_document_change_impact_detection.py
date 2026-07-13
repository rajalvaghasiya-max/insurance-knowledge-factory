"""Create candidate-only revalidation work from a PDF downloader change run."""
from __future__ import annotations

import argparse
from pathlib import Path

from knowledge_domains.product.identity.document_change_impact import DocumentChangeImpactBuilder


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect candidate product impact from changed PDF versions.")
    parser.add_argument("--run-log", type=Path, help="PDF download run log to inspect.")
    args = parser.parse_args()

    result = DocumentChangeImpactBuilder().build(run_log_path=args.run_log)
    report = result["report"]
    print("=" * 70)
    print("DOCUMENT CHANGE IMPACT DETECTION")
    print("=" * 70)
    print(f"Changed document events : {report['changed_document_events']}")
    print(f"Links scanned           : {report['source_product_links_scanned']}")
    print(f"Revalidation candidates : {report['revalidation_candidates']}")
    print(f"Source run log          : {result['run_log_path']}")
    print(f"Registry                : {result['registry_path']}")
    print(f"Report                  : {result['report_path']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
