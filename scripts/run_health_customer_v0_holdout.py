from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

from insurance_intelligence.llm.openai_responses_provider import OpenAIResponsesTextProvider
from insurance_intelligence.llm.provider import LLMTextProvider
from policy_scna_app.health_customer_arithmetic import ask_health_question_with_arithmetic
from policy_scna_app.health_customer_v0 import API_KEY_ENV, MODEL_ENV, HealthConversationContext


DEFAULT_INPUT = Path("health_customer_v0_independent_holdout_v1.json")
DEFAULT_OUTPUT = Path("health_customer_v0_independent_holdout_run_v1.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_holdout(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("benchmark_role") != "HOLDOUT_UNSEEN":
        raise ValueError("holdout benchmark_role must be HOLDOUT_UNSEEN")
    conversations = data.get("conversations")
    if not isinstance(conversations, list) or not conversations:
        raise ValueError("holdout conversations must be a non-empty list")
    return data


def run_holdout(
    *,
    provider: LLMTextProvider,
    model_name: str,
    holdout_path: Path = DEFAULT_INPUT,
    repository_root: Path | None = None,
) -> dict[str, object]:
    source_sha256 = _sha256(holdout_path)
    holdout = _load_holdout(holdout_path)

    cases: list[dict[str, object]] = []
    released_text_count = 0
    clarification_count = 0

    conversations = holdout["conversations"]
    assert isinstance(conversations, list)

    for conversation in conversations:
        if not isinstance(conversation, dict):
            raise ValueError("conversation must be an object")
        conversation_id = str(conversation["conversation_id"])
        raw_cases = conversation.get("cases")
        if not isinstance(raw_cases, list) or not raw_cases:
            raise ValueError(f"conversation {conversation_id} must contain cases")

        context = HealthConversationContext()
        for raw_case in raw_cases:
            if not isinstance(raw_case, dict):
                raise ValueError("case must be an object")
            case_id = str(raw_case["case_id"])
            user_text = str(raw_case["user_text"])
            context_before = len(context.turns)

            result = ask_health_question_with_arithmetic(
                question=user_text,
                provider=provider,
                model_name=model_name,
                request_id=f"holdout-{case_id}",
                execution_id=f"holdout-exec-{case_id}",
                created_at=_utc_now(),
                repository_root=repository_root,
                conversation_context=context,
            )
            context = result.next_context

            if result.released_text:
                released_text_count += 1
            if result.status == "CLARIFICATION":
                clarification_count += 1

            cases.append(
                {
                    "case_id": case_id,
                    "conversation_id": conversation_id,
                    "turn_index": raw_case["turn_index"],
                    "prior_context_required": raw_case["prior_context_required"],
                    "concept_area": raw_case["concept_area"],
                    "user_text": user_text,
                    "reference": raw_case["reference"],
                    "answer_status": result.status,
                    "selected_concept_id": result.selected_concept_id,
                    "selected_topic": result.selected_topic,
                    "render_outcome": result.render_outcome,
                    "context_turn_count_before": context_before,
                    "context_turn_count_after": len(context.turns),
                    "released_text": result.released_text,
                    "quality_scoring": "NOT_SCORED",
                }
            )

    return {
        "schema_version": "1.0",
        "benchmark_id": str(holdout["benchmark_id"]),
        "benchmark_role": "HOLDOUT_RUN",
        "source_holdout_sha256": source_sha256,
        "created_at": _utc_now(),
        "model": model_name,
        "conversation_count": len(conversations),
        "case_count": len(cases),
        "released_text_count": released_text_count,
        "clarification_count": clarification_count,
        "quality_scoring": "NOT_SCORED",
        "cases": cases,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(list(argv) if argv is not None else None)

    api_key = os.environ.get(API_KEY_ENV, "").strip()
    model_name = os.environ.get(MODEL_ENV, "").strip()
    missing = [name for name, value in ((API_KEY_ENV, api_key), (MODEL_ENV, model_name)) if not value]
    if missing:
        raise SystemExit("missing runtime setting(s): " + ", ".join(missing))

    report = run_holdout(
        provider=OpenAIResponsesTextProvider(api_key=api_key),
        model_name=model_name,
        holdout_path=args.input,
        repository_root=Path.cwd(),
    )

    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    output_sha256 = _sha256(args.output)
    print(
        json.dumps(
            {
                "benchmark_id": report["benchmark_id"],
                "source_holdout_sha256": report["source_holdout_sha256"],
                "output_path": str(args.output),
                "output_sha256": output_sha256,
                "model": report["model"],
                "created_at": report["created_at"],
                "case_count": report["case_count"],
                "conversation_count": report["conversation_count"],
                "released_text_count": report["released_text_count"],
                "clarification_count": report["clarification_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
