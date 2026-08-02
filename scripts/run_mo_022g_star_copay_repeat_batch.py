"""Execute a governed repeat-run MO-022G Star copayment batch."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from insurance_intelligence.evaluation.repeat_run_certification import (
    build_repeat_run_evidence,
)
from insurance_intelligence.llm.openai_component_locked import OpenAIComponentLockedProvider
from scripts.run_mo_022g_star_copay_live import (
    build_live_policy,
    build_star_copay_contract,
    result_payload,
    write_result,
)

DEFAULT_OUTPUT_DIR = Path("outputs/evaluation/mo_022g_star_copay_repeat_batch")
DEFAULT_SUMMARY = Path("outputs/evaluation/mo_022g_star_copay_repeat_evidence.json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run governed repeat live certification evidence.")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--audience", default="customer")
    parser.add_argument("--reading-level", default="plain_language")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.runs < 2:
        raise SystemExit("--runs must be at least 2")
    provider = OpenAIComponentLockedProvider.from_environment()
    artifacts: list[dict[str, object]] = []
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for run_index in range(1, args.runs + 1):
        result = provider.evaluate(
            build_star_copay_contract(),
            audience=args.audience,
            reading_level=args.reading_level,
            policy=build_live_policy(),
            certification=None,
        )
        payload = result_payload(result)
        run_path = args.output_dir / f"run_{run_index:02d}.json"
        write_result(run_path, payload)
        artifacts.append(payload)
        print(
            f"Run {run_index}/{args.runs}: "
            f"{result.outcome.routing_result.decision.value} -> {run_path}"
        )

    evidence = build_repeat_run_evidence(artifacts, required_run_count=args.runs)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(evidence.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("=" * 72)
    print("MO-022G STAR COPAY REPEAT-RUN EVIDENCE")
    print("=" * 72)
    print(f"Completed runs       : {evidence.completed_run_count}")
    print(f"Consistent semantics : {evidence.semantically_consistent}")
    print(f"All components match : {evidence.all_components_matched}")
    print(f"Hard failures        : {'NONE' if evidence.hard_failure_free else 'PRESENT'}")
    print(f"Unresolved components: {'NONE' if evidence.unresolved_free else 'PRESENT'}")
    print(f"Minimum confidence   : {evidence.minimum_observed_confidence:.2f}")
    print(f"Status               : {evidence.status}")
    print(f"Summary              : {args.summary}")
    print("Certification        : NOT GRANTED BY THIS BATCH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
