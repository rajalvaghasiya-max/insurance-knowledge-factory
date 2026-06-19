from __future__ import annotations

import argparse
from pathlib import Path

from config.settings import BASE_DIR
from knowledge_domains.health.knowledge_manufacturing.knowledge_manufacturing_engine import KnowledgeManufacturingEngine


def resolve_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return BASE_DIR / path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Department IV — Knowledge Manufacturing Engine")
    parser.add_argument("--processed-document", help="Path to a processed_document_v2.json asset. Defaults to latest processed documents.")
    parser.add_argument("--limit", type=int, default=1, help="Maximum number of processed documents to consume.")
    parser.add_argument("--stage", default="knowledge_blocks", choices=["knowledge_blocks", "concept_recognition"], help="Department IV stage to run.")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing output files.")
    args = parser.parse_args()

    engine = KnowledgeManufacturingEngine()
    result = engine.run(
        processed_document_path=resolve_path(args.processed_document),
        limit=args.limit,
        write=not args.dry_run,
        stage=args.stage,
    )

    print("\n" + "=" * 70)
    print("DEPARTMENT IV — KNOWLEDGE MANUFACTURING")
    print("Stage       :", result["stage"])
    print("Version     :", result["knowledge_manufacturing_engine_version"])
    print("Inputs      :", result["input_count"])
    print("Completed   :", result["completed_count"])
    print("=" * 70)

    for item in result["results"]:
        if result["stage"] == "knowledge_blocks":
            print(f"[{item['status']}] document={item['document_id']} collection={item['collection_path']}")
            print(f"  blocks={item['blocks_created']} quality={item['quality_score']} validation={item['validation_status']}")
            print(f"  report={item['report_path']}")
        else:
            print(f"[{item['status']}] document={item['document_id']} report={item['report_path']}")
            print(f"  recognized={item['recognized_count']} auto={item['auto_approved_count']} review={item['review_required_count']} unknown={item['unknown_count']}")
            queue = item.get("review_queue") or {}
            if queue.get("path"):
                print(f"  review_queue={queue.get('path')} pending={queue.get('pending_count')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
