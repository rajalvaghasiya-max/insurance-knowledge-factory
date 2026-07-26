from __future__ import annotations

import argparse
from pathlib import Path

from knowledge_domains.health.batch.registry_backed_department_iv import (
    RegistryBackedDepartmentIVRunner,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Department IV using registry-backed Department III outputs in an isolated factory scope."
    )
    parser.add_argument("--entity-id", required=True)
    parser.add_argument("--registry-path", required=True)
    parser.add_argument("--factory-dir", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    project_root = Path.cwd()
    runner = RegistryBackedDepartmentIVRunner(
        project_root=project_root,
        registry_path=Path(args.registry_path),
        factory_dir=Path(args.factory_dir),
    )
    result = runner.run(entity_id=args.entity_id, write=not args.dry_run)

    counts = result["status_counts"]
    print("\n" + "=" * 78)
    print("DEPARTMENT IV — REGISTRY-BACKED KNOWLEDGE COMPONENT PIPELINE")
    print("=" * 78)
    print(f"Entity      : {args.entity_id}")
    print(f"Documents   : {result['document_count']}")
    print(f"Completed   : {counts.get('completed', 0)}")
    print(f"Selected    : {counts.get('selected', 0)}")
    print(f"Factory dir : {result['factory_dir']}")
    if not args.dry_run:
        print(f"Registry    : {result['execution_registry_path']}")
    print("-" * 78)
    for item in result["records"]:
        if item["status"] == "completed":
            print(
                f"[completed] {item['document_id']} "
                f"components={item['scanner']['components_created']} "
                f"normalized={item['normalizer']['normalized_components_created']} "
                f"classified={item['classifier']['classified_components_created']}"
            )
        else:
            print(f"[{item['status']}] {item['document_id']}")
    print("=" * 78)


if __name__ == "__main__":
    main()
