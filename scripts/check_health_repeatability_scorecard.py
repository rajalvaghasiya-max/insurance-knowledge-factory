"""Validate and evaluate the frozen Health repeatability scorecard from Issue #355."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_SCORECARD = Path("governance/repeatability/health_repeatability_scorecard.json")
AUTONOMY_LEVELS = {"A0", "A1", "A2", "A3", "A4"}
ALLOWED_ORDINALS = {2, 3, 4, 5}
EXPERIMENT_STATUSES = {"IN_PROGRESS", "COMPLETE"}
CLASSIFICATION_FIELDS = (
    "data_only_count",
    "generic_extension_count",
    "architecture_repair_count",
    "bug_fix_count",
    "product_specific_runtime_count",
)


class RepeatabilityScorecardError(ValueError):
    pass


@dataclass(frozen=True)
class GateEvaluation:
    status: str
    completed_concepts: int
    architecture_repair_total: int
    architecture_repair_average: float | None
    product_specific_runtime_total: int
    consecutive_no_shared_runtime_modification: bool | None
    reasons: tuple[str, ...]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RepeatabilityScorecardError(message)


def _require_nonnegative_int(value: Any, label: str) -> int:
    _require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"{label} must be a non-negative integer")
    return value


def validate_scorecard(data: dict[str, Any]) -> None:
    _require(data.get("schema_version") == "1.0", "schema_version must be '1.0'")
    _require(data.get("gate_issue") == 355, "gate_issue must be 355")
    _require(data.get("experiment_id") == "health-repeatability-v1", "experiment_id must be 'health-repeatability-v1'")

    baseline = data.get("baseline")
    _require(isinstance(baseline, dict), "baseline must be an object")
    _require(baseline.get("ordinal") == 1, "baseline.ordinal must be 1")
    _require(baseline.get("concept_id") == "pre_existing_disease", "baseline.concept_id must be pre_existing_disease")
    _require(
        baseline.get("measurement_status") == "LEGACY_BASELINE_NOT_SCORED",
        "baseline must remain LEGACY_BASELINE_NOT_SCORED",
    )

    experiments = data.get("experiments")
    _require(isinstance(experiments, list), "experiments must be a list")
    ordinals: list[int] = []
    concept_ids: list[str] = []

    for index, item in enumerate(experiments):
        label = f"experiments[{index}]"
        _require(isinstance(item, dict), f"{label} must be an object")
        ordinal = item.get("ordinal")
        _require(ordinal in ALLOWED_ORDINALS, f"{label}.ordinal must be one of {sorted(ALLOWED_ORDINALS)}")
        ordinals.append(ordinal)

        concept_id = item.get("concept_id")
        _require(isinstance(concept_id, str) and concept_id.strip(), f"{label}.concept_id must be non-empty")
        concept_ids.append(concept_id)

        status = item.get("status")
        _require(status in EXPERIMENT_STATUSES, f"{label}.status must be one of {sorted(EXPERIMENT_STATUSES)}")
        autonomy = item.get("front_half_autonomy_level")
        _require(autonomy in AUTONOMY_LEVELS, f"{label}.front_half_autonomy_level must be A0-A4")

        for field in CLASSIFICATION_FIELDS:
            _require_nonnegative_int(item.get(field), f"{label}.{field}")

        _require_nonnegative_int(item.get("repair_cycles_to_first_acceptable_answer"), f"{label}.repair_cycles_to_first_acceptable_answer")
        _require(isinstance(item.get("modified_existing_shared_runtime"), bool), f"{label}.modified_existing_shared_runtime must be boolean")

        questions = item.get("questions")
        _require(isinstance(questions, dict), f"{label}.questions must be an object")
        tested = _require_nonnegative_int(questions.get("tested"), f"{label}.questions.tested")
        acceptable = _require_nonnegative_int(questions.get("acceptable"), f"{label}.questions.acceptable")
        fail_closed = _require_nonnegative_int(questions.get("correct_fail_closed"), f"{label}.questions.correct_fail_closed")
        unacceptable = _require_nonnegative_int(questions.get("unacceptable"), f"{label}.questions.unacceptable")
        _require(
            tested == acceptable + fail_closed + unacceptable,
            f"{label}.questions.tested must equal acceptable + correct_fail_closed + unacceptable",
        )

        authority = item.get("authority_fidelity")
        _require(authority in {"PASS", "FAIL"}, f"{label}.authority_fidelity must be PASS or FAIL")

        if item["product_specific_runtime_count"] > 0:
            _require(
                item["architecture_repair_count"] > 0,
                f"{label}: product-specific runtime count requires architecture_repair_count > 0",
            )

    _require(len(ordinals) == len(set(ordinals)), "experiment ordinals must be unique")
    _require(len(concept_ids) == len(set(concept_ids)), "concept_id values must be unique")


def evaluate_scorecard(data: dict[str, Any]) -> GateEvaluation:
    validate_scorecard(data)
    complete = sorted(
        (item for item in data["experiments"] if item["status"] == "COMPLETE"),
        key=lambda item: item["ordinal"],
    )
    repair_total = sum(item["architecture_repair_count"] for item in complete)
    product_runtime_total = sum(item["product_specific_runtime_count"] for item in complete)
    average = (repair_total / len(complete)) if complete else None
    reasons: list[str] = []

    if product_runtime_total > 0:
        reasons.append("product-specific runtime branch introduced")

    by_ordinal = {item["ordinal"]: item for item in complete}
    if 4 in by_ordinal and 5 in by_ordinal:
        if by_ordinal[4]["architecture_repair_count"] > 0 and by_ordinal[5]["architecture_repair_count"] > 0:
            reasons.append("concepts #4 and #5 both required architecture repair")

    if len(complete) == 4 and average is not None and average > 0.5:
        reasons.append("average architecture repair count exceeds 0.5 per concept")

    consecutive = None
    if len(complete) == 4:
        consecutive = any(
            not by_ordinal[first]["modified_existing_shared_runtime"]
            and not by_ordinal[second]["modified_existing_shared_runtime"]
            for first, second in ((2, 3), (3, 4), (4, 5))
        )
        if not consecutive:
            reasons.append("no two consecutive concepts onboarded without modifying existing shared runtime")

    if reasons:
        status = "PLATFORM_REVIEW"
    elif len(complete) < 4:
        status = "PENDING"
    else:
        status = "PASS"

    return GateEvaluation(
        status=status,
        completed_concepts=len(complete),
        architecture_repair_total=repair_total,
        architecture_repair_average=average,
        product_specific_runtime_total=product_runtime_total,
        consecutive_no_shared_runtime_modification=consecutive,
        reasons=tuple(reasons),
    )


def load_scorecard(path: Path = DEFAULT_SCORECARD) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RepeatabilityScorecardError(str(exc)) from exc
    _require(isinstance(data, dict), "scorecard root must be an object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scorecard", type=Path, default=DEFAULT_SCORECARD)
    parser.add_argument("--json", action="store_true", dest="emit_json")
    args = parser.parse_args()

    try:
        evaluation = evaluate_scorecard(load_scorecard(args.scorecard))
    except RepeatabilityScorecardError as exc:
        print(f"INVALID: {exc}")
        return 1

    payload = {
        "status": evaluation.status,
        "completed_concepts": evaluation.completed_concepts,
        "architecture_repair_total": evaluation.architecture_repair_total,
        "architecture_repair_average": evaluation.architecture_repair_average,
        "product_specific_runtime_total": evaluation.product_specific_runtime_total,
        "consecutive_no_shared_runtime_modification": evaluation.consecutive_no_shared_runtime_modification,
        "reasons": list(evaluation.reasons),
    }
    if args.emit_json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"Health repeatability gate: {evaluation.status}")
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
