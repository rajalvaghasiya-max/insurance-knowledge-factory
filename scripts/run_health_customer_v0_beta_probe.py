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

DEFAULT_MANIFEST = Path("benchmarks/health_customer_v0/beta_probe_batch_01.json")
DEFAULT_OUTPUT = Path("health_customer_v0_beta_probe_batch_01_result.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_manifest(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    root = path.parent
    conversations = [
        json.loads((root / relative).read_text(encoding="utf-8"))
        for relative in manifest["conversation_files"]
    ]
    return manifest, conversations


def run_probe_batch(
    *,
    provider: LLMTextProvider,
    model_name: str,
    manifest_path: Path = DEFAULT_MANIFEST,
    repository_root: Path | None = None,
) -> dict[str, object]:
    manifest, conversations = _load_manifest(manifest_path)
    cases: list[dict[str, object]] = []
    released_text_count = 0
    wrong_concept_count = 0
    clarification_count = 0

    for conversation in conversations:
        conversation_id = str(conversation["conversation_id"])
        context = HealthConversationContext()
        for raw_case in conversation["cases"]:
            case = dict(raw_case)
            expected_concept_id = str(case["expected_concept_id"])
            expected_topic = str(case["expected_topic"])
            context_before = len(context.turns)
            result = ask_health_question_with_arithmetic(
                question=str(case["user_text"]),
                provider=provider,
                model_name=model_name,
                request_id=f"beta-probe-{case['case_id']}",
                execution_id=f"beta-probe-exec-{case['case_id']}",
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

            interpreted = (
                result.interpretation.validated_interpretation.interpretation
                if result.interpretation.validated_interpretation is not None
                else None
            )
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
                    "requested_outcome": (
                        interpreted.requested_outcome if interpreted is not None else None
                    ),
                    "requested_semantic_fact": (
                        interpreted.requested_semantic_fact if interpreted is not None else None
                    ),
                    "scenario_facts": (
                        [
                            {"name": fact.name, "value": fact.value}
                            for fact in interpreted.scenario_facts
                        ]
                        if interpreted is not None
                        else []
                    ),
                    "render_outcome": result.render_outcome,
                    "context_turn_count_before": context_before,
                    "context_turn_count_after": len(context.turns),
                    "released_text": result.released_text,
                    "quality_scoring": "NOT_SCORED",
                }
            )

    expected_case_count = int(manifest["case_count"])
    expected_conversation_count = int(manifest["conversation_count"])
    execution_readiness = (
        "PASS"
        if len(cases) == expected_case_count
        and len(conversations) == expected_conversation_count
        and released_text_count == expected_case_count
        and wrong_concept_count == 0
        else "FAIL"
    )

    return {
        "schema_version": "1.0",
        "batch_id": manifest["batch_id"],
        "evidence_role": manifest["evidence_role"],
        "holdout_eligible": False,
        "created_at": _utc_now(),
        "model": model_name,
        "conversation_count": len(conversations),
        "case_count": len(cases),
        "released_text_count": released_text_count,
        "wrong_concept_count": wrong_concept_count,
        "clarification_count": clarification_count,
        "execution_readiness": execution_readiness,
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
    missing = [
        name
        for name, value in ((API_KEY_ENV, api_key), (MODEL_ENV, model_name))
        if not value
    ]
    if missing:
        raise SystemExit("missing runtime setting(s): " + ", ".join(missing))

    report = run_probe_batch(
        provider=OpenAIResponsesTextProvider(api_key=api_key),
        model_name=model_name,
        manifest_path=args.manifest,
        repository_root=Path.cwd(),
    )
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["execution_readiness"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
