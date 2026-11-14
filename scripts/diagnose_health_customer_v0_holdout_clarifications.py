from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Iterable


DEFAULT_INPUT = Path("health_customer_v0_independent_holdout_run_v1.json")
DEFAULT_OUTPUT = Path("health_customer_v0_holdout_clarification_diagnosis_v1.json")


def _classify_reason(case: dict[str, object]) -> str:
    status = str(case.get("answer_status") or "")
    selected_concept_id = case.get("selected_concept_id")
    text = str(case.get("released_text") or "")

    if status != "CLARIFICATION":
        return "NOT_CLARIFICATION"

    if selected_concept_id is None and text.startswith(
        "I could not understand the insurance concept confidently enough to answer safely."
    ):
        return "semantic_interpretation_clarification"

    if selected_concept_id is None and text.startswith(
        "I understood the question only partially and do not have a safely resolved insurance concept."
    ):
        return "missing_selected_concept"

    if selected_concept_id is not None and text.startswith(
        "I understand the insurance topic, but the specific part of the question is ambiguous across insurance concepts."
    ):
        return "cross_concept_component_rejected"

    if selected_concept_id is not None and "I do not yet have an approved customer explanation" in text:
        return "approved_education_missing"

    return "UNCLASSIFIED_CLARIFICATION"


def build_diagnosis(run_path: Path) -> dict[str, object]:
    run = json.loads(run_path.read_text(encoding="utf-8"))
    cases = run.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("run artifact must contain non-empty cases")

    rows: list[dict[str, object]] = []
    reasons: Counter[str] = Counter()
    selected_count = 0

    for raw_case in cases:
        if not isinstance(raw_case, dict):
            raise ValueError("case must be an object")
        reason = _classify_reason(raw_case)
        reasons[reason] += 1
        if raw_case.get("selected_concept_id") is not None:
            selected_count += 1
        rows.append(
            {
                "case_id": raw_case["case_id"],
                "answer_status": raw_case.get("answer_status"),
                "selected_concept_id": raw_case.get("selected_concept_id"),
                "selected_topic": raw_case.get("selected_topic"),
                "render_outcome": raw_case.get("render_outcome"),
                "clarification_reason": reason,
            }
        )

    return {
        "schema_version": "1.0",
        "source_run": str(run_path),
        "case_count": len(rows),
        "selected_concept_count": selected_count,
        "clarification_reason_counts": dict(sorted(reasons.items())),
        "cases": rows,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(list(argv) if argv is not None else None)

    diagnosis = build_diagnosis(args.input)
    args.output.write_text(json.dumps(diagnosis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "case_count": diagnosis["case_count"],
        "selected_concept_count": diagnosis["selected_concept_count"],
        "clarification_reason_counts": diagnosis["clarification_reason_counts"],
        "output_path": str(args.output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
