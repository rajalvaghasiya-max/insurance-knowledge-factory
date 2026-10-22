from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Iterable

from insurance_intelligence.llm.openai_responses_provider import OpenAIResponsesTextProvider
from insurance_intelligence.llm.provider import LLMTextProvider
from policy_scna_app.health_customer_arithmetic import ask_health_question_with_arithmetic
from policy_scna_app.health_customer_v0 import (
    API_KEY_ENV,
    MODEL_ENV,
    HealthConversationContext,
)

DEFAULT_MANIFEST = Path("benchmarks/health_customer_v0/dev_benchmark_36_v1.json")
DEFAULT_OUTPUT = Path("health_customer_v0_dev36_live_result.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_conversations(manifest_path: Path) -> list[dict[str, object]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = manifest_path.parent
    conversations: list[dict[str, object]] = []
    for relative in manifest["conversation_files"]:
        conversations.append(json.loads((root / relative).read_text(encoding="utf-8")))
    return conversations


def run_benchmark(
    *,
    provider: LLMTextProvider,
    model_name: str,
    manifest_path: Path = DEFAULT_MANIFEST,
    repository_root: Path | None = None,
) -> dict[str, object]:
    conversations = _load_conversations(manifest_path)
    cases: list[dict[str, object]] = []
    released_text_count = 0
    wrong_concept_count = 0
    clarification_count = 0

    for conversation in conversations:
        conversation_id = str(conversation["conversation_id"])
        context = HealthConversationContext()
        for raw_case in conversation["cases"]:  # type: ignore[index]
            case = dict(raw_case)
            expected_concept_id = str(case["expected_concept_id"])
            expected_topic = str(case["expected_topic"])
            context_before = len(context.turns)
            result = ask_health_question_with_arithmetic(
                question=str(case["user_text"]),
                provider=provider,
                model_name=model_name,
                request_id=f"dev36-{case['case_id']}",
                execution_id=f"dev36-exec-{case['case_id']}",
                created_at=_utc_now(),
                repository_root=repository_root,
                conversation_context=context,
            )
            context = result.next_context
            route_match = (
                result.selected_concept_id == expected_concept_id
                and result.selected_topic == expected_topic
            )
            if result.released_text:
                released_text_count += 1
            if not route_match:
                wrong_concept_count += 1
            if result.status == "CLARIFICATION":
                clarification_count += 1
            interpretation = result.interpretation.validated_interpretation
            interpreted = interpretation.interpretation if interpretation is not None else None
            cases.append(
                {
                    "case_id": case["case_id"],
                    "conversation_id": conversation_id,
                    "turn_index": case["turn_index"],
                    "prior_context_required": case["prior_context_required"],
                    "concept_area": case["concept_area"],
                    "user_text": case["user_text"],
                    "expected_concept_id": expected_concept_id,
                    "expected_topic": expected_topic,
                    "selected_concept_id": result.selected_concept_id,
                    "selected_topic": result.selected_topic,
                    "route_match": route_match,
                    "answer_status": result.status,
                    "interpretation_status": (
                        interpreted.interpretation_status if interpreted is not None else None
                    ),
                    "render_outcome": result.render_outcome,
                    "context_turn_count_before": context_before,
                    "context_turn_count_after": len(context.turns),
                    "released_text": result.released_text,
                    "quality_scoring": "NOT_SCORED",
                }
            )

    case_count = len(cases)
    conversation_count = len(conversations)
    product_path_readiness = (
        "PASS"
        if case_count == 36
        and conversation_count == 12
        and released_text_count == case_count
        and wrong_concept_count == 0
        else "FAIL"
    )
    return {
        "schema_version": "1.0",
        "benchmark_id": "health-customer-v0-dev-36-live-v1",
        "benchmark_role": "DEV_ONLY",
        "created_at": _utc_now(),
        "model": model_name,
        "conversation_count": conversation_count,
        "case_count": case_count,
        "released_text_count": released_text_count,
        "wrong_concept_count": wrong_concept_count,
        "clarification_count": clarification_count,
        "product_path_readiness": product_path_readiness,
        "quality_scoring": "NOT_SCORED",
        "cases": cases,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(list(argv) if argv is not None else None)

    api_key = os.environ.get(API_KEY_ENV, "").strip()
    model_name = os.environ.get(MODEL_ENV, "").strip()
    missing = [name for name, value in ((API_KEY_ENV, api_key), (MODEL_ENV, model_name)) if not value]
    if missing:
        raise SystemExit("missing runtime setting(s): " + ", ".join(missing))

    report = run_benchmark(
        provider=OpenAIResponsesTextProvider(api_key=api_key),
        model_name=model_name,
        manifest_path=args.manifest,
        repository_root=Path.cwd(),
    )
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["product_path_readiness"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
