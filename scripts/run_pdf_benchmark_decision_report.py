"""Build the durable P1.6 benchmark decision report."""
from __future__ import annotations

import argparse
from pathlib import Path

from config.settings import BASE_DIR
from knowledge_domains.health.benchmark.pdf_benchmark_decision_report import PdfBenchmarkDecisionReport


def main() -> None:
    parser = argparse.ArgumentParser(description="Build P1.6 PDF benchmark decision report.")
    parser.add_argument("--benchmark-report-path", help="Repository-relative or absolute benchmark report path.")
    args = parser.parse_args()
    source = Path(args.benchmark_report_path) if args.benchmark_report_path else None
    if source is not None and not source.is_absolute():
        source = BASE_DIR / source
    result = PdfBenchmarkDecisionReport(base_dir=BASE_DIR).build(benchmark_report_path=source)
    report = result["report"]
    print("=" * 70)
    print("P1.6 PDF BENCHMARK DECISION REPORT")
    print("=" * 70)
    print(f"Cases evaluated       : {report['cohort']['case_count']}/{report['cohort']['target_case_count']}")
    print(f"Parser strategy       : {report['decision']['parser_strategy_status']}")
    print(f"OCR policy            : {report['decision']['ocr_policy']}")
    print(f"Unbounded ready       : {report['decision_gates']['benchmark_ready_for_unbounded_parser_strategy']}")
    print(f"Report                : {result['report_path']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
