from __future__ import annotations

import argparse

from knowledge_domains.health.routing.registry_backed_evidence_router import RegistryBackedEvidenceRouter


def main() -> None:
    parser = argparse.ArgumentParser(description="Route Health evidence from scoped Department IV components.")
    parser.add_argument("--entity-id", required=True)
    parser.add_argument("--field", required=True)
    parser.add_argument("--registry-path", required=True, help="Registry-backed Factory Input Registry path.")
    parser.add_argument("--factory-dir", required=True, help="Scoped factory directory containing Department IV registry.")
    parser.add_argument("--limit", type=int, default=12, help="Candidate lines to print.")
    args = parser.parse_args()

    router = RegistryBackedEvidenceRouter()
    plan = router.resolve_routing_plan(
        entity_id=args.entity_id,
        field=args.field,
        factory_dir=args.factory_dir,
        factory_input_registry_path=args.registry_path,
    )
    output_path = router.write_routing_plan(plan, args.factory_dir)

    print()
    print("=" * 78)
    print("REGISTRY-BACKED EVIDENCE ROUTER")
    print("=" * 78)
    print(f"Entity      : {args.entity_id}")
    print(f"Field       : {args.field}")
    print(f"Documents   : {plan['bundle_count']}")
    print(f"Candidates  : {plan['candidate_count']}")
    print(f"Output      : {output_path}")
    print("Priority    : " + " > ".join(plan["priority_sources"]))
    print("-" * 78)
    for item in plan["candidates"][: args.limit]:
        hits = ", ".join(item.get("field_hits", [])[:4])
        print(
            f"[{item['source_type']}] [score={item['routing_score']}] "
            f"[section={item['section'] or 'unknown'}] [{hits}] "
            f"{item['classified_component_id']}"
        )
    print("=" * 78)


if __name__ == "__main__":
    main()
