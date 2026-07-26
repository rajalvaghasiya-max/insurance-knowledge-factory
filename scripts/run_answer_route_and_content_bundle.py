from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.customer_document_intelligence.answer_route_decision import (
    AnswerRouteDecisionEngine,
)
from knowledge_domains.health.customer_document_intelligence.approved_content_bundle import (
    ApprovedContentBundleAssembler,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create a deterministic answer route and approved LLM content bundle "
            "from a governed interpretation packet."
        )
    )
    parser.add_argument("--interpretation-packet", required=True)
    parser.add_argument("--route-output", required=True)
    parser.add_argument("--bundle-output", required=True)
    args = parser.parse_args()

    packet_path = Path(args.interpretation_packet)
    route_path = Path(args.route_output)
    bundle_path = Path(args.bundle_output)

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    route = AnswerRouteDecisionEngine().decide(packet)
    bundle = ApprovedContentBundleAssembler().assemble(
        packet=packet,
        route_decision=route,
    )

    route_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    route_path.write_text(
        json.dumps(route, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    bundle_path.write_text(
        json.dumps(bundle, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )

    print("=" * 72)
    print("ANSWER ROUTE + APPROVED CONTENT BUNDLE")
    print("=" * 72)
    print(f"Interpretation Packet : {packet_path}")
    print(f"Route Output          : {route_path}")
    print(f"Bundle Output         : {bundle_path}")
    print(f"Route                 : {route['route']}")
    print(f"Decision ID           : {route['decision_id']}")
    print(f"Bundle ID             : {bundle['bundle_id']}")
    print(f"Runtime Examples      : {bundle['example_policy']['runtime_generation_allowed']}")


if __name__ == "__main__":
    main()
