from __future__ import annotations

import argparse
import json
from pathlib import Path

from factory_sdk.golden_concept_pipeline import GoldenConceptManufacturingPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PolicyScna Golden Concept Manufacturing Pipeline v2.0")
    parser.add_argument("--concept-id", default="copay", help="Concept ID to manufacture")
    parser.add_argument(
        "--distillation-dir",
        default="knowledge/factory/distillation/reports",
        help="Directory containing KDE *_distillation_report.json files",
    )
    parser.add_argument(
        "--output-dir",
        default="knowledge/factory/golden_concepts/copay",
        help="Output directory for Golden Concept package files",
    )
    args = parser.parse_args()

    pipeline = GoldenConceptManufacturingPipeline()
    outputs = pipeline.run_from_dir(
        distillation_dir=args.distillation_dir,
        concept_id=args.concept_id,
        output_dir=args.output_dir,
    )

    certification = json.loads(Path(outputs["certification"]).read_text(encoding="utf-8"))
    package = json.loads(Path(outputs["golden_concept_package"]).read_text(encoding="utf-8"))
    queue = json.loads(Path(outputs["manufacturing_queue"]).read_text(encoding="utf-8"))
    state = json.loads(Path(outputs["manufacturing_state"]).read_text(encoding="utf-8"))
    execution = json.loads(Path(outputs["execution_log"]).read_text(encoding="utf-8"))

    print("\n" + "=" * 72)
    print("GOLDEN CONCEPT MANUFACTURING PIPELINE v2.0 — ACTIVE ORCHESTRATION")
    print("=" * 72)
    print(f"Concept             : {args.concept_id}")
    print(f"Tasks Planned       : {queue['task_count']}")
    print(f"Package             : {outputs['golden_concept_package']}")
    print(f"Certification       : {certification['status']}")
    print(f"Execution Results   : {state['summary']}")
    print("-" * 72)
    print(f"Queue               : {outputs['manufacturing_queue']}")
    print(f"Dependency Graph    : {outputs['dependency_graph']}")
    print(f"Dispatch Plan       : {outputs['dispatch_plan']}")
    print(f"Certification File  : {outputs['certification']}")
    print(f"Execution Log       : {outputs['execution_log']}")
    print(f"Manufacturing State : {outputs['manufacturing_state']}")
    print("-" * 72)
    for asset_type, task_ids in package["components_by_asset_type"].items():
        print(f"{asset_type}: {len(task_ids)} task(s)")


if __name__ == "__main__":
    main()
