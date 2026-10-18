"""Run the six preregistered Health Customer v0 dev-seed questions through the real product path.

This is evaluation tooling only. It does not score customer quality, alter routing, or
create insurance authority. Literal released text is captured exactly as returned by
``policy_scna_app.ask_health_question`` after Rendering Exit Safety.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

from insurance_intelligence.llm.openai_responses_provider import OpenAIResponsesTextProvider
from policy_scna_app.health_customer_v0 import (
    API_KEY_ENV,
    MODEL_ENV,
    ask_health_question,
)

DEFAULT_BENCHMARK = Path("benchmarks/health_customer_v0/dev_seed_reference_v1.json")

EXPECTED_ROUTE = {
    "pre_existing_disease": ("health:concept:pre_existing_disease", "pre_existing_disease"),
    "waiting_period": ("health:concept:waiting_period", "waiting_period"),
    "restoration": ("health:concept:restoration", "restoration"),
    "room_rent_limit": ("health:concept:room_rent_limit", "room_rent_limit"),
    "bariatric_surgery": ("health:concept:bariatric_surgery", "bariatric_surgery"),
    "copayment": ("health:concept:copayment", "conditional_copayment"),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_dev_seed_cases(path: str | Path = DEFAULT_BENCHMARK) -> tuple[dict[str, str], ...]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if raw.get("schema_version") != "1.0" or raw.get("benchmark_role") != "DEV_ONLY":
        raise ValueError("unexpected Health Customer v0 dev-seed benchmark metadata")
    cases = raw.get("cases")
    if not isinstance(cases, list) or len(cases) != 6:
        raise ValueError("Health Customer v0 dev-seed benchmark must contain exactly six cases")

    normalized = []
    seen = set()
    for item in cases:
        if not isinstance(item, dict):
            raise ValueError("benchmark cases must be objects")
        case_id = item.get("case_id")
        concept_area = item.get("concept_area")
        user_text = item.get("user_text")
        if not all(isinstance(value, str) and value.strip() for value in (case_id, concept_area, user_text)):
            raise ValueError("each benchmark case requires case_id, concept_area, and user_text")
        if case_id in seen:
            raise ValueError(f"duplicate case_id: {case_id}")
        if concept_area not in EXPECTED_ROUTE:
            raise ValueError(f"unsupported dev-seed concept_area: {concept_area}")
        seen.add(case_id)
        normalized.append(
            {
                "case_id": case_id,
                "concept_area": concept_area,
                "user_text": user_text,
            }
        )
    return tuple(normalized)


def run_dev_seed(*, api_key: str, model_name: str, benchmark_path: str | Path = DEFAULT_BENCHMARK) -> dict[str, object]:
    if not api_key.strip():
        raise ValueError("api_key must be non-empty")
    if not model_name.strip():
        raise ValueError("model_name must be non-empty")

    provider = OpenAIResponsesTextProvider(api_key=api_key.strip())
    results = []
    wrong_concept_count = 0
    released_count = 0

    for item in load_dev_seed_cases(benchmark_path):
        expected_concept_id, expected_topic = EXPECTED_ROUTE[item["concept_area"]]
        result = ask_health_question(
            question=item["user_text"],
            provider=provider,
            model_name=model_name.strip(),
            request_id=f"health-customer-v0-{item['case_id']}",
            execution_id=f"health-customer-v0-{item['case_id']}-execution",
        )
        route_match = (
            result.selected_concept_id == expected_concept_id
            and result.selected_topic == expected_topic
        )
        if not route_match:
            wrong_concept_count += 1
        if result.released_text.strip():
            released_count += 1

        results.append(
            {
                "case_id": item["case_id"],
                "concept_area": item["concept_area"],
                "user_text": item["user_text"],
                "expected_concept_id": expected_concept_id,
                "expected_topic": expected_topic,
                "selected_concept_id": result.selected_concept_id,
                "selected_topic": result.selected_topic,
                "route_match": route_match,
                "answer_status": result.status,
                "interpretation_status": result.interpretation.status,
                "render_outcome": result.render_outcome,
                "released_text": result.released_text,
            }
        )

    return {
        "schema_version": "1.0",
        "benchmark_id": "health-customer-v0-dev-seed-live-v1",
        "benchmark_role": "DEV_ONLY",
        "created_at": _utc_now(),
        "model": model_name.strip(),
        "case_count": len(results),
        "released_text_count": released_count,
        "wrong_concept_count": wrong_concept_count,
        "product_path_readiness": (
            "PASS" if released_count == len(results) and wrong_concept_count == 0 else "FAIL"
        ),
        "quality_scoring": "NOT_SCORED",
        "cases": results,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", default=str(DEFAULT_BENCHMARK))
    parser.add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    api_key = os.environ.get(API_KEY_ENV, "").strip()
    model_name = os.environ.get(MODEL_ENV, "").strip()
    missing = [name for name, value in ((API_KEY_ENV, api_key), (MODEL_ENV, model_name)) if not value]
    if missing:
        print("LIVE_RUN_INVALID: missing runtime setting(s): " + ", ".join(missing), file=sys.stderr)
        return 2

    try:
        payload = run_dev_seed(
            api_key=api_key,
            model_name=model_name,
            benchmark_path=args.benchmark,
        )
    except Exception as exc:
        print(f"LIVE_RUN_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["product_path_readiness"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
