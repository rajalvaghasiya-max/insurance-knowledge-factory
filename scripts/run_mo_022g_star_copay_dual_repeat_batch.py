"""Run a governed repeat batch for the MO-022G dual-extractor Star case."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from insurance_intelligence.evaluation.dual_extractor_repeat_run import (
    build_dual_extractor_repeat_run_evidence,
)
from insurance_intelligence.llm.openai_dual_extractor import OpenAIDualExtractorProvider
from scripts.run_mo_022g_star_copay_dual_extractor import result_payload
from scripts.run_mo_022g_star_copay_live import build_live_policy, build_star_copay_contract, write_result


DEFAULT_RUN_DIR = Path("outputs/evaluation/mo_022g_star_copay_dual_repeat_batch")
DEFAULT_OUTPUT = Path("outputs/evaluation/mo_022g_star_copay_dual_repeat_evidence.json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run governed dual-extractor repeat evidence.")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audience", default="customer")
    parser.add_argument("--reading-level", default="plain_language")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.runs < 2:
        raise SystemExit("--runs must be at least 2")
    provider = OpenAIDualExtractorProvider.from_environment()
    artifacts: list[dict[str, object]] = []
    for index in range(1, args.runs + 1):
        result = provider.evaluate(
            build_star_copay_contract(),
            audience=args.audience,
            reading_level=args.reading_level,
            policy=build_live_policy(),
            certification=None,
        )
        payload = result_payload(result)
        run_path = args.run_dir / f"run_{index:02d}.json"
        write_result(run_path, payload)
        artifacts.append(payload)
        print(f"Completed run {index}/{args.runs}: {run_path}")

    evidence = build_dual_extractor_repeat_run_evidence(
        artifacts,
        required_run_count=args.runs,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(asdict(evidence), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("=" * 72)
    print("MO-022G DUAL-EXTRACTOR REPEAT-RUN EVIDENCE")
    print("=" * 72)
    print(f"Completed runs        : {evidence.completed_run_count}")
    print(f"Exact agreement       : {evidence.exact_agreement_every_run}")
    print(f"All components matched: {evidence.all_components_matched}")
    print(f"Hard failures         : {'NONE' if evidence.hard_failure_free else 'PRESENT'}")
    print(f"Unresolved components : {'NONE' if evidence.unresolved_free else 'PRESENT'}")
    print(f"Minimum confidence    : {evidence.minimum_observed_confidence:.2f}")
    print(f"Status                : {evidence.status}")
    print(f"Output                : {args.output}")
    print("Certification         : NOT GRANTED BY THIS BATCH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
