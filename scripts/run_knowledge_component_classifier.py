"""
Run Department IV - Knowledge Component Classifier v1.0

Usage:
    python -m scripts.run_knowledge_component_classifier
    python -m scripts.run_knowledge_component_classifier --normalized-component-collection <path>
    python -m scripts.run_knowledge_component_classifier --dry-run
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from knowledge_domains.health.knowledge_manufacturing.knowledge_component_classifier import KnowledgeComponentClassifier


def find_latest_normalized_collection(project_root: Path) -> Path:
    directory = project_root / "knowledge" / "factory" / "normalized_knowledge_components"
    if not directory.exists():
        raise FileNotFoundError(
            "No normalized_knowledge_components directory found. "
            "Run python -m scripts.run_knowledge_component_normalizer first."
        )
    candidates = sorted(directory.glob("*_normalized_component_collection.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(
            "No normalized component collection found. "
            "Run python -m scripts.run_knowledge_component_normalizer first."
        )
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Department IV Knowledge Component Classifier.")
    parser.add_argument(
        "--normalized-component-collection",
        dest="normalized_component_collection",
        default=None,
        help="Path to a normalized knowledge component collection JSON file.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Run without writing output files.")
    args = parser.parse_args()

    project_root = Path.cwd()
    source_path = Path(args.normalized_component_collection) if args.normalized_component_collection else find_latest_normalized_collection(project_root)

    classifier = KnowledgeComponentClassifier(project_root=project_root)
    collection, report = classifier.classify_file(source_path, dry_run=args.dry_run)

    print("\n" + "=" * 70)
    print("DEPARTMENT IV — KNOWLEDGE COMPONENT CLASSIFIER")
    print("=" * 70)
    print(f"Source      : {source_path}")
    print(f"Input       : {report['normalized_components_received']}")
    print(f"Classified  : {report['classified_components_created']}")
    print(f"Active      : {report['active_components']}")
    print(f"Metadata    : {report['metadata_components']}")
    print(f"Noise       : {report['noise_components']}")
    print(f"Low Conf    : {report['low_confidence_components']}")
    print(f"Quality     : {report['quality_score']}")
    print(f"Validation  : {report['validation_status']}")
    print("----------------------------------------------------------------------")
    for key, value in sorted(report.get("classification_type_counts", {}).items()):
        print(f"{key:12}: {value}")
    print("----------------------------------------------------------------------")
    if args.dry_run:
        print("Dry Run     : no files written")
    else:
        print(f"Collection  : {report['classified_collection_path']}")
        report_path = classifier._report_path(collection, report)
        print(f"Report      : {report_path}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
