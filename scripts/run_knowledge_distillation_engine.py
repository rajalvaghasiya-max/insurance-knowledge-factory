from __future__ import annotations

import argparse
import json
from pathlib import Path

from knowledge_domains.health.knowledge_distillation.knowledge_distillation_engine import KnowledgeDistillationEngine
from knowledge_domains.health.knowledge_distillation.observation_reader import ObservationReader


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PolicyScna Knowledge Distillation Engine v1.0")
    parser.add_argument(
        "--input",
        default="knowledge/factory/observations/copay/copay_observation_register_sample.json",
        help="Path to observation register JSON",
    )
    parser.add_argument(
        "--output-dir",
        default="knowledge/factory/distillation/reports",
        help="Directory for distillation reports",
    )
    args = parser.parse_args()

    reader = ObservationReader()
    observations = reader.read_file(args.input)
    engine = KnowledgeDistillationEngine()
    reports = engine.distill_many(observations)
    paths = engine.write_reports(reports, args.output_dir)

    summary = {
        "engine": "Knowledge Distillation Engine",
        "version": "1.0",
        "input": args.input,
        "output_dir": args.output_dir,
        "observations": len(observations),
        "reports": len(paths),
        "average_knowledge_potential": round(sum(r.knowledge_potential.overall for r in reports) / max(1, len(reports)), 2),
        "review_required": sum(1 for r in reports if r.review_required),
        "top_reports": [
            {
                "distillation_id": r.distillation_id,
                "observation_id": r.observation.observation_id,
                "knowledge_potential": r.knowledge_potential.overall,
                "opportunities": [o.asset_type for o in r.manufacturing_opportunities],
            }
            for r in sorted(reports, key=lambda x: x.knowledge_potential.overall, reverse=True)[:5]
        ],
    }
    summary_path = Path(args.output_dir) / "knowledge_distillation_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 70)
    print("KNOWLEDGE DISTILLATION ENGINE v1.0")
    print("=" * 70)
    print(f"Input Observations : {len(observations)}")
    print(f"Reports Generated  : {len(paths)}")
    print(f"Average KPS        : {summary['average_knowledge_potential']}")
    print(f"Review Required    : {summary['review_required']}")
    print(f"Summary            : {summary_path}")
    print("-" * 70)
    for item in summary["top_reports"]:
        print(f"{item['observation_id']} | KPS {item['knowledge_potential']} | {', '.join(item['opportunities'][:4])}")


if __name__ == "__main__":
    main()
