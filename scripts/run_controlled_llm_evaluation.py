"""Execute the first bounded MO-022F provider run and export auditable traces."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from insurance_intelligence.contracts.llm_evaluation import ModelParameter
from insurance_intelligence.evaluation.dataset import load_evaluation_dataset
from insurance_intelligence.evaluation.harness import (
    ControlledHarnessConfig,
    execute_controlled_cases,
)
from insurance_intelligence.evaluation.openai_provider import OpenAIResponsesProvider


DEFAULT_DATASET = Path("tests/fixtures/insurance_intelligence/llm_evaluation")
DEFAULT_OUTPUT = Path("outputs/evaluation/mo_022f_openai_first_run.json")
DEFAULT_MODEL = "gpt-5-mini-2025-08-07"
DEFAULT_PROMPT_VERSION = "mo-022f-controlled-rendering-v1"


def _serialise(value: object) -> object:
    if hasattr(value, "value"):
        return getattr(value, "value")
    raise TypeError(f"unsupported value: {type(value).__name__}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--run-number", type=int, default=1)
    args = parser.parse_args()

    dataset = load_evaluation_dataset(args.dataset)
    cases = tuple(case for case in dataset.cases if case.reference_output is not None)
    if not cases:
        raise SystemExit("No materialized reference-output cases are available")

    config = ControlledHarnessConfig(
        provider="openai",
        model=args.model,
        model_version=args.model,
        prompt_version=DEFAULT_PROMPT_VERSION,
        parameters=(
            ModelParameter(name="reasoning_effort", value="low"),
            ModelParameter(name="max_output_tokens", value="500"),
        ),
        timeout_seconds=args.timeout_seconds,
    )
    outputs = execute_controlled_cases(
        cases,
        provider=OpenAIResponsesProvider.from_environment(),
        config=config,
        run_number=args.run_number,
    )
    payload = {
        "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.dataset_version,
        "provider": config.provider,
        "model": config.model,
        "model_version": config.model_version,
        "prompt_version": config.prompt_version,
        "run_number": args.run_number,
        "case_count": len(outputs),
        "outputs": [asdict(item) for item in outputs],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=_serialise),
        encoding="utf-8",
    )
    print(f"Saved controlled provider traces: {args.output}")
    print(f"Cases: {len(outputs)}")
    for item in outputs:
        print(
            f"{item.trace.case_id}: {item.trace.status.value} / "
            f"{item.deterministic_result.verdict.value}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
