"""Run the governed Star copay case with OpenAI and Gemini extractors."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from time import sleep

from insurance_intelligence.llm.gemini_semantic_extractor import GeminiSemanticExtractorError
from insurance_intelligence.llm.openai_component_locked import OpenAIComponentLockedError
from insurance_intelligence.llm.openai_gemini_cross_provider import OpenAIGeminiCrossProvider
from scripts.run_mo_022g_star_copay_live import build_live_policy, build_star_copay_contract


DEFAULT_OUTPUT = Path("outputs/evaluation/mo_022g_star_copay_openai_gemini.json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run governed OpenAI + Gemini semantic fidelity.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audience", default="customer")
    parser.add_argument("--reading-level", default="plain_language")
    parser.add_argument("--data-classification", choices=("PUBLIC", "SYNTHETIC"), default="PUBLIC")
    parser.add_argument("--max-attempts", type=int, default=3)
    return parser


def _evaluate_with_retries(args: argparse.Namespace):
    if args.max_attempts < 1 or args.max_attempts > 5:
        raise SystemExit("--max-attempts must be between 1 and 5")
    provider = OpenAIGeminiCrossProvider.from_environment()
    for attempt in range(1, args.max_attempts + 1):
        try:
            return provider.evaluate(
                build_star_copay_contract(),
                audience=args.audience,
                reading_level=args.reading_level,
                policy=build_live_policy(),
                certification=None,
                data_classification=args.data_classification,
            )
        except (OpenAIComponentLockedError, GeminiSemanticExtractorError) as exc:
            if attempt >= args.max_attempts:
                raise
            delay_seconds = 2 ** (attempt - 1)
            print(
                f"Transient provider failure on attempt {attempt}/{args.max_attempts}: {exc}"
            )
            print(f"Retrying after {delay_seconds} second(s)...")
            sleep(delay_seconds)
    raise RuntimeError("unreachable")


def main() -> int:
    args = _parser().parse_args()
    result = _evaluate_with_retries(args)
    payload = {
        "schema_version": "1.0",
        "run_type": "MO-022G_OPENAI_GEMINI_CROSS_PROVIDER",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data_classification": args.data_classification,
        "certification_effect": "NONE",
        "certification_granted": False,
        "renderer_trace": asdict(result.rendering_trace),
        "openai_extractor_trace": asdict(result.openai_extractor_trace),
        "gemini_extractor_trace": asdict(result.gemini_extractor_trace),
        "agreements": [asdict(item) for item in result.agreements],
        "semantic_report": asdict(result.outcome.fidelity_report),
        "routing_result": asdict(result.outcome.routing_result),
        "human_review_packet": asdict(result.outcome.human_review_packet) if result.outcome.human_review_packet else None,
        "verified_explanation": asdict(result.outcome.verified_explanation) if result.outcome.verified_explanation else None,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    disagreed = [item.component_id for item in result.agreements if not item.agreed]
    print("=" * 72)
    print("MO-022G OPENAI + GEMINI CROSS-PROVIDER RUN")
    print("=" * 72)
    print(f"Routing decision     : {result.outcome.routing_result.decision.value}")
    print(f"Reason codes         : {', '.join(result.outcome.routing_result.reason_codes)}")
    print(f"Cross-provider match : {'EXACT' if not disagreed else 'DISAGREED'}")
    print(f"Disagreed components : {', '.join(disagreed) if disagreed else 'NONE'}")
    print(f"Data classification  : {args.data_classification}")
    print(f"Output               : {args.output}")
    print("Certification        : NOT GRANTED BY THIS RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
