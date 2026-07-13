from __future__ import annotations

import argparse

from knowledge_domains.health.batch.registry_backed_intake import RegistryBackedProductIntake


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a non-destructive intake plan for registry-backed product evidence.")
    parser.add_argument("--entity-id", default="bajaj_allianz_general:my_health_care")
    args = parser.parse_args()
    result = RegistryBackedProductIntake().build(entity_id=args.entity_id)
    report = result["report"]
    print("=" * 70)
    print("REGISTRY-BACKED PRODUCT EVIDENCE INTAKE")
    print("=" * 70)
    print(f"Entity                : {report['entity_id']}")
    print(f"Registry documents    : {report['intake_count']}")
    print(f"Ready for processing  : {report['status_counts']['ready_for_processing']}")
    print(f"Missing archive files : {report['status_counts']['blocked_missing_archive_file']}")
    print(f"Registry              : {result['registry_path']}")
    print(f"Report                : {result['report_path']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
