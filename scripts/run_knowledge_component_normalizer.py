from __future__ import annotations

import argparse
from pathlib import Path

from knowledge_domains.health.knowledge_manufacturing.knowledge_component_normalizer import (
    KnowledgeComponentNormalizerRunner,
)


def find_latest_component_collection(root: Path) -> Path:
    components_dir = root / "knowledge" / "factory" / "knowledge_components"
    if not components_dir.exists():
        raise FileNotFoundError(
            "No knowledge_components folder found. Run Knowledge Component Scanner first."
        )
    candidates = sorted(
        components_dir.glob("*_knowledge_component_collection.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(
            "No raw knowledge component collection found in knowledge/factory/knowledge_components."
        )
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Department IV — Knowledge Component Normalizer v1.0"
    )
    parser.add_argument(
        "--component-collection",
        help="Path to raw knowledge component collection. If omitted, latest collection is used.",
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
    collection_path = (
        Path(args.component_collection)
        if args.component_collection
        else find_latest_component_collection(project_root)
    )

    print("\n" + "=" * 70)
    print("DEPARTMENT IV — KNOWLEDGE COMPONENT NORMALIZER")
    print("=" * 70)
    print(f"Input       : {collection_path}")
    print("Machine     : Knowledge Component Normalizer v1.0")
    print("Boundary    : normalized components only; no insurance semantic interpretation")

    if args.dry_run:
        print("Dry Run     : true")
        print("=" * 70)
        return

    runner = KnowledgeComponentNormalizerRunner(project_root=project_root)
    result = runner.run(collection_path)
    report = result["report"]

    print("-" * 70)
    print(f"Raw In      : {report.raw_components_received}")
    print(f"Normalized  : {report.normalized_components_created}")
    print(f"Merged      : {report.components_merged}")
    print(f"Dup Groups  : {report.duplicate_groups}")
    print(f"Dup Shadow  : {report.duplicate_shadow_components}")
    print(f"Noise       : {report.noise_components}")
    print(f"Metadata    : {report.metadata_components}")
    print(f"Active      : {report.active_components}")
    print(f"XRefs       : {report.cross_references_preserved}")
    print(f"Quality     : {report.quality_score}")
    print(f"Validation  : {report.validation_status}")
    print(f"Collection  : {result['collection_path']}")
    print(f"Report      : {result['report_path']}")
    print(f"Next        : {report.next_stage}")
    print("=" * 70)


if __name__ == "__main__":
    main()
