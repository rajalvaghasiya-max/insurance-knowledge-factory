"""Run the credential-gated GSI P1 live genericity benchmark against OpenAI.

This script is intentionally not part of CI. It requires an explicit API key and
model at runtime and prints no raw provider output.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Mapping

from insurance_intelligence.contracts.semantic_interpretation import audit_artifact_as_dict
from insurance_intelligence.llm.openai_responses_provider import OpenAIResponsesTextProvider
from insurance_intelligence.semantic_interpretation.provider_adapter import (
    GovernedInterpretationVocabulary,
    interpret_with_provider,
)
from insurance_intelligence.terminology.health_seed import HEALTH_CONCEPTS_V1

API_KEY_ENV = "OPENAI_API_KEY"
MODEL_ENV = "POLICYSCNA_GSI_MODEL"
CONFIG_ID = "gsi-p1b-openai-live-v1"
HELD_BACK_CONCEPT_ID = "health:concept:restoration"


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    user_text: str
    expected_concept_id: str
    held_back: bool = False


CASES: tuple[BenchmarkCase, ...] = (
    BenchmarkCase(
        "ped-paraphrase-1",
        "I already had diabetes before I bought the policy. What does insurance call that kind of condition?",
        "health:concept:pre_existing_disease",
    ),
    BenchmarkCase(
        "ped-paraphrase-2",
        "What is the insurance term for an illness that existed before my health cover started?",
        "health:concept:pre_existing_disease",
    ),
    BenchmarkCase(
        "bariatric-paraphrase-1",
        "What is the policy benefit for surgery used to treat severe obesity called?",
        "health:concept:bariatric_surgery",
    ),
    BenchmarkCase(
        "room-rent-paraphrase-1",
        "Which policy concept decides what hospital room category I am allowed to take?",
        "health:concept:room_rent_limit",
    ),
    BenchmarkCase(
        "restoration-held-back-1",
        "What is the feature called when my available health cover can fill back up after it gets used?",
        HELD_BACK_CONCEPT_ID,
        True,
    ),
    BenchmarkCase(
        "restoration-held-back-2",
        "Which benefit can replenish the sum insured after a claim has consumed some of it?",
        HELD_BACK_CONCEPT_ID,
        True,
    ),
)


@dataclass(frozen=True)
class LiveConfig:
    api_key: str
    model: str


def live_config_from_env(env: Mapping[str, str]) -> LiveConfig:
    api_key = env.get(API_KEY_ENV, "").strip()
    model = env.get(MODEL_ENV, "").strip()
    missing = [name for name, value in ((API_KEY_ENV, api_key), (MODEL_ENV, model)) if not value]
    if missing:
        raise RuntimeError(
            "live benchmark not executed; missing explicit runtime setting(s): " + ", ".join(missing)
        )
    return LiveConfig(api_key=api_key, model=model)


def benchmark_vocabulary() -> GovernedInterpretationVocabulary:
    return GovernedInterpretationVocabulary(
        concept_ids=tuple(item.concept_id for item in HEALTH_CONCEPTS_V1),
        intent_ids=("understand_policy_term", "understand_policy_effect"),
        semantic_fact_ids=("definition", "applicability", "consequence", "mechanics"),
        scenario_fact_names=("context_detail",),
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_benchmark(*, config: LiveConfig) -> dict[str, object]:
    provider = OpenAIResponsesTextProvider(api_key=config.api_key)
    vocabulary = benchmark_vocabulary()
    results: list[dict[str, object]] = []
    for index, case in enumerate(CASES, start=1):
        result = interpret_with_provider(
            request_id=f"gsi-live-{case.case_id}",
            user_text=case.user_text,
            vocabulary=vocabulary,
            provider=provider,
            model_name=config.model,
            config_id=CONFIG_ID,
            execution_id=f"gsi-live-execution-{index}",
            created_at=_utc_now(),
            timeout_seconds=30.0,
        )
        selected_concept_id = None
        confidence = None
        interpretation_status = None
        requested_outcome = None
        requested_semantic_fact = None
        request_authority_class = None
        if result.validated_interpretation is not None:
            interpretation = result.validated_interpretation.interpretation
            selected_concept_id = interpretation.selected_concept_id
            confidence = interpretation.confidence
            interpretation_status = interpretation.interpretation_status
            requested_outcome = interpretation.requested_outcome
            requested_semantic_fact = interpretation.requested_semantic_fact
            request_authority_class = interpretation.request_authority_class
        passed = result.status == "RESOLVED" and selected_concept_id == case.expected_concept_id
        results.append(
            {
                "case_id": case.case_id,
                "held_back": case.held_back,
                "expected_concept_id": case.expected_concept_id,
                "attempt_status": result.status,
                "interpretation_status": interpretation_status,
                "selected_concept_id": selected_concept_id,
                "confidence": confidence,
                "requested_outcome": requested_outcome,
                "requested_semantic_fact": requested_semantic_fact,
                "request_authority_class": request_authority_class,
                "passed": passed,
                "audit_artifact": audit_artifact_as_dict(result.audit_artifact),
            }
        )

    held_back = [item for item in results if item["held_back"]]
    return {
        "schema_version": "1.0",
        "benchmark_id": CONFIG_ID,
        "provider": provider.provider_name,
        "model": config.model,
        "held_back_concept_id": HELD_BACK_CONCEPT_ID,
        "case_count": len(results),
        "passed_count": sum(1 for item in results if item["passed"]),
        "all_passed": all(bool(item["passed"]) for item in results),
        "held_back_all_passed": bool(held_back) and all(bool(item["passed"]) for item in held_back),
        "results": results,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="optional JSON report path; stdout is always emitted")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = live_config_from_env(os.environ)
    except RuntimeError as exc:
        print(str(exc))
        return 2
    report = run_benchmark(config=config)
    rendered = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["all_passed"] and report["held_back_all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
