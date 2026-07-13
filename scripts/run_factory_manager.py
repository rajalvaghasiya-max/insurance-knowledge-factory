from __future__ import annotations

import argparse
import json

from knowledge_domains.health.factory.factory_manager import FactoryManager


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PolicyScna Factory Manager.")
    parser.add_argument(
        "--action",
        choices=["init", "plan", "init-and-plan"],
        default="init-and-plan",
        help="Factory Manager action to run.",
    )
    parser.add_argument("--entity-id", default=None, help="Optional entity filter.")
    parser.add_argument("--registry-path", default=None, help="Optional evidence/factory input registry path.")
    parser.add_argument("--factory-dir", default=None, help="Optional factory run directory.")
    parser.add_argument("--stage", default=None, help="Optional pipeline stage filter.")
    parser.add_argument("--limit", type=int, default=None, help="Optional max jobs to plan.")
    parser.add_argument("--print-json", action="store_true", help="Print full JSON output.")

    args = parser.parse_args()
    manager = FactoryManager(registry_path=args.registry_path, factory_dir=args.factory_dir)

    init_result = None
    queue = None

    if args.action in {"init", "init-and-plan"}:
        init_result = manager.initialize_factory(write=True)

    if args.action in {"plan", "init-and-plan"}:
        queue = manager.plan_jobs(
            entity_id=args.entity_id,
            stage=args.stage,
            limit=args.limit,
            write=True,
        )

    print()
    print("=" * 70)
    print("POLICYSCNA FACTORY MANAGER")
    print("=" * 70)
    print(f"Action      : {args.action}")

    if init_result:
        print(f"Documents   : {init_result['document_count']}")
        print(f"Initialized : {init_result['initialized_count']}")
        print(f"Registry    : {init_result['registry_path']}")

    if queue:
        print(f"Jobs        : {queue['job_count']}")
        print(f"Queue       : {manager.paths.queue_path}")
        print(f"Event Log   : {manager.paths.event_log_path}")
        print("-" * 70)
        for job in queue["jobs"][:20]:
            entity_text = ", ".join(job.get("entity_ids", []))
            print(
                f"[{job['stage']}] [{job['assigned_engine']}] "
                f"[authority={job['authority_score']}] [{entity_text}] "
                f"{job['relative_path']}"
            )

    print("=" * 70)

    if args.print_json:
        print(json.dumps({"init": init_result, "queue": queue}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
