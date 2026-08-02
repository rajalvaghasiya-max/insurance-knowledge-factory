"""Run repeated governed OpenAI+Gemini Star copay evaluations."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from insurance_intelligence.contracts.rule_family_registry import (
    build_conditional_copayment_family,
)
from insurance_intelligence.evaluation.cross_provider_repeat_run import (
    build_cross_provider_repeat_run_evidence,
)
from insurance_intelligence.llm.governed_cross_provider import (
    GovernedCrossProviderEvaluator,
)
from insurance_intelligence.llm.openai_gemini_cross_provider import (
    OpenAIGeminiCrossProvider,
)
from scripts.run_mo_022g_star_copay_live import (
    build_live_policy,
    build_star_copay_contract,
)
from scripts.run_mo_022g_star_copay_openai_gemini import (
    build_star_copay_family_binding,
)


DEFAULT_OUTPUT = Path("outputs/evaluation/mo_022g_star_copay_openai_gemini_repeat_batch.json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run repeated governed OpenAI+Gemini Star copay evaluations."
    )
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audience", default="customer")
    parser.add_argument("--reading-level", default="plain_language")
    parser.add_argument(
        "--data-classification", choices=("PUBLIC", "SYNTHETIC"), default="PUBLIC"
    )
    return parser


def _run_artifact(
    args: argparse.Namespace, evaluator: GovernedCrossProviderEvaluator
) -> dict[str, object]:
    contract = build_star_copay_contract()
    result = evaluator.evaluate(
        contract,
        audience=args.audience,
        reading_level=args.reading_level,
        policy=build_live_policy(),
        certification=None,
        data_classification=args.data_classification,
    )
    return {
        "schema_version": "1.0",
        "run_type": "MO-022G_OPENAI_GEMINI_CROSS_PROVIDER",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data_classification": args.data_classification,
        "certification_effect": "NONE",
        "certification_granted": False,
        "rule_family_preflight": {
            "family_id": evaluator.family.family_id,
            "family_version": evaluator.family.version,
            "status": "PASSED",
        },
        "renderer_trace": asdict(result.rendering_trace),
        "openai_extractor_trace": asdict(result.openai_extractor_trace),
        "gemini_extractor_trace": asdict(result.gemini_extractor_trace),
        "agreements": [asdict(item) for item in result.agreements],
        "semantic_report": asdict(result.outcome.fidelity_report),
        "routing_result": asdict(result.outcome.routing_result),
        "human_review_packet": (
            asdict(result.outcome.human_review_packet)
            if result.outcome.human_review_packet else None
        ),
        "verified_explanation": (
            asdict(result.outcome.verified_explanation)
            if result.outcome.verified_explanation else None
        ),
    }


def main() -> int:
    args = _parser().parse_args()
    if args.runs < 2 or args.runs > 10:
        raise SystemExit("--runs must be between 2 and 10")

    evaluator = GovernedCrossProviderEvaluator(
        provider=OpenAIGeminiCrossProvider.from_environment(),
        family=build_conditional_copayment_family(),
        binding=build_star_copay_family_binding(),
    )
    artifacts: list[dict[str, object]] = []
    for index in range(1, args.runs + 1):
        print(f"Running governed cross-provider case {index}/{args.runs}...")
        artifacts.append(_run_artifact(args, evaluator))

    evidence = build_cross_provider_repeat_run_evidence(
        artifacts, required_run_count=args.runs
    )
    payload = {
        "schema_version": "1.0",
        "run_type": "MO-022G_OPENAI_GEMINI_REPEAT_BATCH",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runs": artifacts,
        "stability_evidence": evidence.to_dict(),
        "certification_effect": "NONE",
        "certification_granted": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )

    print("=" * 72)
    print("MO-022G OPENAI + GEMINI REPEAT BATCH")
    print("=" * 72)
    print(f"Status                    : {evidence.status}")
    print(f"Exact agreement every run : {evidence.exact_agreement_every_run}")
    print(f"All components matched    : {evidence.all_components_matched}")
    print(f"Hard-failure free          : {evidence.hard_failure_free}")
    print(f"Unresolved free            : {evidence.unresolved_free}")
    print(f"Preflight passed           : {evidence.preflight_passed_every_run}")
    print(f"Minimum confidence         : {evidence.minimum_observed_confidence:.2f}")
    print(f"Output                     : {args.output}")
    print("Certification              : NOT GRANTED BY THIS BATCH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
