"""Run the credential-gated GSI P1 live genericity benchmark against OpenAI.

This runner produces interpretation/genericity evidence only. It intentionally does
not declare the strategic P1 safety/quality verdict. Held-back restoration cases
must be supplied as an external, SHA-256-pinned blind pack; there is no fallback.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
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
CONFIG_ID = "gsi-p1c-openai-live-genericity-v1"
HELD_BACK_CONCEPT_ID = "health:concept:restoration"


class BenchmarkIntegrityError(RuntimeError):
    """Raised when benchmark preconditions are not trustworthy enough to run."""


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    user_text: str
    expected_concept_id: str
    held_back: bool = False


BASE_CASES: tuple[BenchmarkCase, ...] = (
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


def _canonical_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load_blind_held_back_pack(*, path: Path, expected_sha256: str) -> tuple[BenchmarkCase, ...]:
    """Load externally authored restoration cases or fail closed before any provider call."""
    if not path.is_file():
        raise BenchmarkIntegrityError("blind held-back benchmark pack is missing")
    expected = expected_sha256.strip().lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise BenchmarkIntegrityError("expected blind-pack SHA-256 must be 64 lowercase hex characters")
    actual = _canonical_sha256(path)
    if actual != expected:
        raise BenchmarkIntegrityError("blind held-back benchmark pack SHA-256 mismatch")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError("blind held-back benchmark pack is not valid JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0":
        raise BenchmarkIntegrityError("blind held-back benchmark pack schema_version must be 1.0")
    if payload.get("concept_id") != HELD_BACK_CONCEPT_ID:
        raise BenchmarkIntegrityError("blind held-back benchmark pack concept_id is not the held-back concept")
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or len(raw_cases) < 3:
        raise BenchmarkIntegrityError("blind held-back benchmark pack must contain at least three cases")

    seen: set[str] = set()
    cases: list[BenchmarkCase] = []
    for item in raw_cases:
        if not isinstance(item, dict):
            raise BenchmarkIntegrityError("blind held-back benchmark cases must be objects")
        case_id = item.get("case_id")
        user_text = item.get("user_text")
        if not isinstance(case_id, str) or not case_id.strip() or case_id in seen:
            raise BenchmarkIntegrityError("blind held-back benchmark case_id must be unique and non-empty")
        if not isinstance(user_text, str) or not user_text.strip():
            raise BenchmarkIntegrityError("blind held-back benchmark user_text must be non-empty")
        seen.add(case_id)
        cases.append(BenchmarkCase(case_id.strip(), user_text.strip(), HELD_BACK_CONCEPT_ID, True))
    return tuple(cases)


def benchmark_vocabulary() -> GovernedInterpretationVocabulary:
    return GovernedInterpretationVocabulary(
        concept_ids=tuple(item.concept_id for item in HEALTH_CONCEPTS_V1),
        intent_ids=("understand_policy_term", "understand_policy_effect"),
        semantic_fact_ids=("definition", "applicability", "consequence", "mechanics"),
        scenario_fact_names=("context_detail",),
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_benchmark(*, config: LiveConfig, held_back_cases: tuple[BenchmarkCase, ...], held_back_pack_sha256: str) -> dict[str, object]:
    if not held_back_cases or not all(case.held_back for case in held_back_cases):
        raise BenchmarkIntegrityError("externally loaded held-back cases are required")
    provider = OpenAIResponsesTextProvider(api_key=config.api_key)
    vocabulary = benchmark_vocabulary()
    cases = BASE_CASES + held_back_cases
    results: list[dict[str, object]] = []
    for index, case in enumerate(cases, start=1):
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
                "interpretation_correct": passed,
                "audit_artifact": audit_artifact_as_dict(result.audit_artifact),
            }
        )

    held_back = [item for item in results if item["held_back"]]
    genericity_passed = bool(held_back) and all(bool(item["interpretation_correct"]) for item in held_back)
    return {
        "schema_version": "1.1",
        "benchmark_id": CONFIG_ID,
        "provider": provider.provider_name,
        "model": config.model,
        "held_back_concept_id": HELD_BACK_CONCEPT_ID,
        "held_back_pack_sha256": held_back_pack_sha256,
        "case_count": len(results),
        "interpretation_passed_count": sum(1 for item in results if item["interpretation_correct"]),
        "genericity_verdict": "PASS" if genericity_passed else "FAIL",
        "strategic_p1_verdict": "NOT_SCORED",
        "strategic_p1_verdict_reason": "released-text safety and independent customer-quality evidence are scored separately",
        "results": results,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blind-pack", required=True, help="external blind held-back JSON pack")
    parser.add_argument("--blind-pack-sha256", required=True, help="precommitted SHA-256 of blind pack")
    parser.add_argument("--output", help="optional JSON report path; stdout is always emitted")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = live_config_from_env(os.environ)
        held_back_cases = load_blind_held_back_pack(
            path=Path(args.blind_pack), expected_sha256=args.blind_pack_sha256
        )
    except (RuntimeError, BenchmarkIntegrityError) as exc:
        print(f"INVALID: {exc}")
        return 2
    report = run_benchmark(
        config=config,
        held_back_cases=held_back_cases,
        held_back_pack_sha256=args.blind_pack_sha256.lower(),
    )
    report_json = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False)
    print(report_json)
    if args.output:
        Path(args.output).write_text(report_json + "\n", encoding="utf-8")
    return 0 if report["genericity_verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
