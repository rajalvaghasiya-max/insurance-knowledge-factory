from __future__ import annotations

import argparse
from pathlib import Path

from knowledge_domains.health.benchmark.pdf_benchmark_selected_parser import PdfBenchmarkSelectedParser


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse selected P1.6 benchmark PDFs without creating product knowledge.")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    result = PdfBenchmarkSelectedParser(base_dir=Path(args.repository_root).resolve()).build(force=args.force)
    report = result["report"]
    counts = report["status_counts"]
    print("=" * 70)
    print("P1.6 SELECTED PDF BENCHMARK PARSING")
    print("=" * 70)
    print(f"Selected cases : {report['selected_case_count']}")
    print(f"Parsed         : {counts['parsed']}")
    print(f"Reused         : {counts['reused']}")
    print(f"Blocked        : {counts['blocked']}")
    print(f"Failed         : {counts['failed']}")
    print(f"Report         : {result['report_path']}")
    print(f"Parse registry : {result['parse_registry_path']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
