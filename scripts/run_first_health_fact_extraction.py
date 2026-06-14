from __future__ import annotations

import argparse
import json
from pathlib import Path

from config.settings import BASE_DIR
from knowledge_domains.health.extractors.ped_waiting_period_extractor import PedWaitingPeriodExtractor


def safe_entity_id(entity_id: str) -> str:
    return (
        entity_id.replace(":", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
        .lower()
    )


def main():
    parser = argparse.ArgumentParser(
        description="Run first evidence-backed health fact extraction."
    )

    parser.add_argument(
        "--entity-id",
        default="aditya_birla_health:activ_one",
        help="Entity/product ID for extracted fact.",
    )

    parser.add_argument(
        "--search-root",
        default=".",
        help="Folder to scan. Example: parsed, knowledge, archive, or a product folder.",
    )

    args = parser.parse_args()

    entity_id = args.entity_id
    search_root = BASE_DIR / args.search_root

    extractor = PedWaitingPeriodExtractor()
    result = extractor.extract_from_search_root(
        entity_id=entity_id,
        search_root=search_root,
    )

    output_dir = BASE_DIR / "knowledge" / "health" / "extracted_facts"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{safe_entity_id(entity_id)}_ped_waiting_period.json"

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 70)
    print("FIRST HEALTH FACT EXTRACTION")
    print("=" * 70)
    print(f"Entity      : {entity_id}")
    print(f"Search root : {search_root}")
    print(f"Status      : {result.get('status')}")
    print(f"Output      : {output_path}")

    if result.get("status") == "extracted":
        fact = result["fact"]
        print(f"Field       : {fact.get('field')}")
        print(f"Value       : {fact.get('value')} {fact.get('unit')}")
        print(f"Source      : {fact.get('source', {}).get('source_file_path')}")
        print(f"Validation  : {fact.get('validation', {}).get('status')}")
        print(f"Review      : {fact.get('validation', {}).get('review_recommendation')}")
    else:
        print(f"Message     : {result.get('message')}")

    print("=" * 70)


if __name__ == "__main__":
    main()
