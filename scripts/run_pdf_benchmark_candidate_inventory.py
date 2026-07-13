from __future__ import annotations

import argparse

from knowledge_domains.health.batch.pdf_benchmark_candidate_inventory import PdfBenchmarkCandidateInventory


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory official Health PDFs for P1.6 benchmark candidate selection.")
    parser.add_argument("--insurer-id", action="append", dest="insurer_ids", help="Repeat to limit scope. Default: Aditya Birla Health and Bajaj Allianz General.")
    args = parser.parse_args()

    result = PdfBenchmarkCandidateInventory().build(insurer_ids=args.insurer_ids)
    summary = result["inventory"]["summary"]
    print("=" * 70)
    print("P1.6 PDF BENCHMARK CANDIDATE INVENTORY")
    print("=" * 70)
    print(f"Registry entries selected : {summary['registry_entries_selected']}")
    print(f"Raw files readable        : {summary['raw_files_readable']}")
    print(f"Missing raw files         : {summary['missing_raw_files']}")
    print(f"Unreadable files          : {summary['unreadable_files']}")
    print(f"Output                   : {result['output_path']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
