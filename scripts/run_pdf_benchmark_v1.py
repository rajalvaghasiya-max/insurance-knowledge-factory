"""Run P1.6 native-text PDF benchmark v1."""
from __future__ import annotations
import argparse
from pathlib import Path
from config.settings import BASE_DIR
from knowledge_domains.health.benchmark.pdf_benchmark_v1 import PdfBenchmarkV1

def main() -> None:
    parser = argparse.ArgumentParser(description="Run P1.6 PDF benchmark v1.")
    parser.add_argument("--manifest-path", help="Repository-relative or absolute manifest path.")
    args = parser.parse_args()
    manifest = Path(args.manifest_path) if args.manifest_path else None
    if manifest is not None and not manifest.is_absolute():
        manifest = BASE_DIR / manifest
    result = PdfBenchmarkV1(base_dir=BASE_DIR).build(manifest_path=manifest)
    report = result["report"]
    print("=" * 70)
    print("P1.6 PDF BENCHMARK V1")
    print("=" * 70)
    print(f"Cases evaluated       : {report['case_count']}/{report['target_case_count']}")
    print(f"Decision ready        : {report['benchmark_readiness']['ready_for_decision']}")
    print(f"Native text usable    : {report['status_counts']['native_text_usable']}")
    print(f"Review required       : {report['status_counts']['native_text_review_required']}")
    print(f"Blocked               : {report['status_counts']['blocked']}")
    print(f"Report                : {result['report_path']}")
    print(f"Registry              : {result['registry_path']}")
    print("=" * 70)
if __name__ == '__main__':
    main()
