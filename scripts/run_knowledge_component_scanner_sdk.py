from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.knowledge_manufacturing.knowledge_component_scanner_sdk import (
    KnowledgeComponentScannerSDKRunner,
)


def find_latest_processed_document(root: Path) -> Path:
    processed_dir = root / "knowledge" / "factory" / "processed_documents"
    if not processed_dir.exists():
        raise FileNotFoundError(
            "No processed_documents folder found. Run Department III document processing first."
        )

    candidates = sorted(
        processed_dir.glob("*_processed_document_v2.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        candidates = sorted(
            processed_dir.glob("*_processed_document*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    if not candidates:
        raise FileNotFoundError("No processed document JSON found in knowledge/factory/processed_documents.")
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Department IV — Knowledge Component Scanner SDK Adapter v1.0"
    )
    parser.add_argument(
        "--processed-document",
        help="Path to a processed document asset. If omitted, latest processed document is used.",
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root. Default: current directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show selected input only; do not write output.",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    processed_path = (
        Path(args.processed_document)
        if args.processed_document
        else find_latest_processed_document(project_root)
    )

    print("\n" + "=" * 70)
    print("DEPARTMENT IV — KNOWLEDGE COMPONENT SCANNER SDK")
    print("=" * 70)
    print(f"Input       : {processed_path}")
    print("Machine     : Knowledge Component Scanner SDK Adapter v1.0")
    print("Boundary    : raw components only; no insurance semantic interpretation")

    if args.dry_run:
        print("Dry Run     : true")
        print("=" * 70)
        return

    runner = KnowledgeComponentScannerSDKRunner(project_root=project_root)
    result = runner.run(processed_path)

    report = json.loads(Path(result["report"]).read_text(encoding="utf-8"))
    certification = json.loads(Path(result["certification"]).read_text(encoding="utf-8"))
    stats = report.get("statistics", {})

    print("-" * 70)
    print(f"Components  : {stats.get('components_created')}")
    print(f"Sections    : {stats.get('source_sections_processed')}")
    print(f"Tables      : {stats.get('source_tables_processed')}")
    print(f"Duplicates  : {stats.get('duplicate_components')}")
    print(f"Noise       : {stats.get('noise_components')}")
    print(f"XRefs       : {stats.get('cross_references_preserved')}")
    print(f"Quality     : {report.get('quality_score')}")
    print(f"Validation  : {report.get('validation_status')}")
    print(f"Cert Status : {certification.get('validation_status')}")
    print(f"Asset       : {result['asset']}")
    print(f"Report      : {result['report']}")
    print(f"Cert        : {result['certification']}")
    print(f"Event       : {result['event']}")
    print(f"Next        : {report.get('next_stage')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
