from __future__ import annotations

import argparse
import json

from config.settings import BASE_DIR
from knowledge_domains.health.routing.evidence_router import EvidenceRouter


def main():
    parser = argparse.ArgumentParser(description="Run Evidence Router search plan.")
    parser.add_argument("--entity-id", default="aditya_birla_health:activ_one")
    parser.add_argument("--field", default="copay")
    parser.add_argument(
        "--base-roots",
        nargs="*",
        default=["knowledge", "parsed", "archive"],
        help="Base roots to scan."
    )

    args = parser.parse_args()

    router = EvidenceRouter()
    plan = router.resolve_search_plan(
        entity_id=args.entity_id,
        field=args.field,
        base_roots=args.base_roots,
    )

    output_dir = BASE_DIR / "knowledge" / "health" / "routing_plans"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_entity = args.entity_id.replace(":", "_").replace("/", "_").replace("\\", "_").lower()
    output_path = output_dir / f"{safe_entity}_{args.field}_routing_plan.json"

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 70)
    print("EVIDENCE ROUTER")
    print("=" * 70)
    print(f"Entity      : {args.entity_id}")
    print(f"Field       : {args.field}")
    print(f"Version     : {plan['router_version']}")
    print(f"Candidates  : {plan['candidate_count']}")
    print(f"Rejected    : {plan['rejected_counts']}")
    print(f"Output      : {output_path}")
    print("Priority    : " + " > ".join(plan["priority_sources"]))

    for item in plan["candidates"][:20]:
        print(f"[{item['source_type']}] [{item['match_reason']}] {item['relative_path']}")

    print("=" * 70)


if __name__ == "__main__":
    main()
