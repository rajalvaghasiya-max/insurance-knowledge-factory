"""Run one governed MO-022G Star copay case with independent dual extraction."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from insurance_intelligence.llm.openai_dual_extractor import (
    OpenAIDualExtractorProvider,
    OpenAIDualExtractorResult,
)
from scripts.run_mo_022g_star_copay_live import build_live_policy, build_star_copay_contract


DEFAULT_OUTPUT = Path("outputs/evaluation/mo_022g_star_copay_dual_extractor.json")


def result_payload(result: OpenAIDualExtractorResult) -> dict[str, object]:
    """Serialize one dual-extractor result into the governed local artifact shape."""
    return {
        "schema_version": "1.0",
        "run_type": "MO-022G_DUAL_EXTRACTOR_LIVE_CERTIFICATION",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "certification_effect": "NONE",
        "certification_granted": False,
        "renderer_trace": asdict(result.rendering_trace),
        "extractor_a_trace": asdict(result.extractor_a_trace),
        "extractor_b_trace": asdict(result.extractor_b_trace),
        "agreements": [asdict(item) for item in result.agreements],
        "semantic_report": asdict(result.outcome.fidelity_report),
        "routing_result": asdict(result.outcome.routing_result),
        "human_review_packet": (
            asdict(result.outcome.human_review_packet)
            if result.outcome.human_review_packet is not None
            else None
        ),
        "verified_explanation": (
            asdict(result.outcome.verified_explanation)
            if result.outcome.verified_explanation is not None
            else None
        ),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one governed MO-022G Star copay dual-extractor case."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audience", default="customer")
    parser.add_argument("--reading-level", default="plain_language")
    return parser


def main() -> int:
    args = _parser().parse_args()
    provider = OpenAIDualExtractorProvider.from_environment()
    result = provider.evaluate(
        build_star_copay_contract(),
        audience=args.audience,
        reading_level=args.reading_level,
        policy=build_live_policy(),
        certification=None,
    )
    payload = result_payload(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    disagreed = [item.component_id for item in result.agreements if not item.agreed]
    routing = result.outcome.routing_result
    print("=" * 72)
    print("MO-022G STAR COPAY DUAL-EXTRACTOR LIVE RUN")
    print("=" * 72)
    print(f"Routing decision   : {routing.decision.value}")
    print(f"Reason codes       : {', '.join(routing.reason_codes)}")
    print(f"Extractor agreement: {'EXACT' if not disagreed else 'DISAGREED'}")
    print(f"Disagreed components: {', '.join(disagreed) if disagreed else 'NONE'}")
    print(f"Output             : {args.output}")
    print("Certification      : NOT GRANTED BY THIS RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
