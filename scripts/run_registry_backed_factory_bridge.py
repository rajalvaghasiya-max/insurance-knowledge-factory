from __future__ import annotations

import argparse

from knowledge_domains.health.batch.registry_backed_factory_bridge import RegistryBackedFactoryBridge


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Department III factory inputs from registry-backed PDF parse artifacts."
    )
    parser.add_argument("--entity-id", required=True, help="Registered product entity ID.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and report without writing outputs.")
    args = parser.parse_args()

    result = RegistryBackedFactoryBridge().build(entity_id=args.entity_id, write=not args.dry_run)
    report = result["report"]

    print()
    print("=" * 70)
    print("REGISTRY-BACKED FACTORY BRIDGE")
    print("=" * 70)
    print(f"Entity                     : {report['entity_id']}")
    print(f"Ready for Department III   : {report['status_counts']['ready_for_department_03']}")
    print(f"Blocked                    : {report['status_counts']['blocked']}")
    print(f"Factory input registry     : {report['factory_input_registry']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
