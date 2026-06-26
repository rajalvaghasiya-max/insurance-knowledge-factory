"""
Run Department IV - Knowledge Topic Composer v1.0

Usage:
    python -m scripts.run_knowledge_topic_composer
    python -m scripts.run_knowledge_topic_composer --classified-component-collection <path>
    python -m scripts.run_knowledge_topic_composer --dry-run
"""

from __future__ import annotations

import argparse
from pathlib import Path

from knowledge_domains.health.knowledge_manufacturing.knowledge_topic_composer import KnowledgeTopicComposer


def find_latest_classified_collection(project_root: Path) -> Path:
    directory = project_root / "knowledge" / "factory" / "classified_knowledge_components"
    if not directory.exists():
        raise FileNotFoundError(
            "No classified_knowledge_components directory found. "
            "Run python -m scripts.run_knowledge_component_classifier first."
        )
    candidates = sorted(directory.glob("*_classified_component_collection.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(
            "No classified component collection found. "
            "Run python -m scripts.run_knowledge_component_classifier first."
        )
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Department IV Knowledge Topic Composer.")
    parser.add_argument(
        "--classified-component-collection",
        dest="classified_component_collection",
        default=None,
        help="Path to a classified knowledge component collection JSON file.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Run without writing output files.")
    args = parser.parse_args()

    project_root = Path.cwd()
    source_path = Path(args.classified_component_collection) if args.classified_component_collection else find_latest_classified_collection(project_root)

    composer = KnowledgeTopicComposer(project_root=project_root)
    collection, report = composer.compose_file(source_path, dry_run=args.dry_run)

    print("\n" + "=" * 70)
    print("DEPARTMENT IV — KNOWLEDGE TOPIC COMPOSER")
    print("=" * 70)
    print(f"Source      : {source_path}")
    print(f"Input       : {report['classified_components_received']}")
    print(f"Assigned    : {report['components_assigned']}")
    print(f"Skipped     : {report['components_skipped']}")
    print(f"Topics      : {report['topics_created']}")
    print(f"Incomplete  : {report['incomplete_topics']}")
    print(f"Orphans     : {report['orphan_components']}")
    print(f"Avg/Topic   : {report['average_components_per_topic']}")
    print(f"Largest     : {report['largest_topic_component_count']}")
    print(f"Cohesion    : {report['average_cohesion_score']}")
    print(f"Quality     : {report['quality_score']}")
    print(f"Validation  : {report['validation_status']}")
    print("----------------------------------------------------------------------")
    for key, value in sorted(report.get("topic_type_counts", {}).items()):
        print(f"{key:18}: {value}")
    print("----------------------------------------------------------------------")
    if args.dry_run:
        print("Dry Run     : no files written")
    else:
        print(f"Collection  : {report['topic_collection_path']}")
        report_path = composer._report_path(collection, report)
        print(f"Report      : {report_path}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
