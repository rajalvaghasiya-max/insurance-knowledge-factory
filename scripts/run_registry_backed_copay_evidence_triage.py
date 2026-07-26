from __future__ import annotations

import argparse
import json
from pathlib import Path

from config.settings import BASE_DIR
from knowledge_domains.health.routing.copay_evidence_triage import CopayEvidenceTriage


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else BASE_DIR / path


def main() -> None:
    parser = argparse.ArgumentParser(description="Triage a registry-backed copay routing plan.")
    parser.add_argument("--routing-plan", required=True, help="Path to registry-backed copay routing plan JSON.")
    parser.add_argument("--factory-dir", required=True, help="Scoped factory directory used for output.")
    args = parser.parse_args()

    routing_path = resolve_path(args.routing_plan)
    plan = json.loads(routing_path.read_text(encoding="utf-8"))
    triage = CopayEvidenceTriage().triage_plan(plan)
    output_path = CopayEvidenceTriage().write_triage(triage, args.factory_dir)

    counts = triage["status_counts"]
    print("=" * 78)
    print("REGISTRY-BACKED COPAY EVIDENCE TRIAGE")
    print("=" * 78)
    print(f"Entity              : {triage['entity_id']}")
    print(f"Input candidates    : {triage['input_candidate_count']}")
    print(f"Decision-bearing    : {triage['decision_bearing_count']}")
    print(f"Supporting context  : {triage['supporting_context_count']}")
    print(f"Rejected            : {triage['rejected_count']}")
    print(f"Output              : {output_path}")
    print("-" * 78)
    for item in triage["decision_bearing_candidates"]:
        labels = ", ".join(item.get("condition_labels") or []) or "unlabelled"
        percentages = ", ".join(item.get("triage_signals", {}).get("percentages") or [])
        print(f"[decision] [{labels}] [{percentages}] {item.get('classified_component_id')}")
    print("=" * 78)


if __name__ == "__main__":
    main()
