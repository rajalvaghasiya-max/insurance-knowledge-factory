from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


VALIDATOR_VERSION = "0.4"

CRITICAL_FIELDS = [
    "metadata.product_name",
    "metadata.uin",
    "waiting_periods.pre_existing_disease_waiting_period",
    "waiting_periods.specified_disease_waiting_period",
    "waiting_periods.initial_waiting_period",
    "product_facts.copay",
    "product_facts.room_rent_limit",
]

MIN_CONFIDENCE = 0.90


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def is_placeholder_uin(value: Any) -> bool:
    if not value or not isinstance(value, str):
        return True

    cleaned = value.strip().upper()

    if "XXXXX" in cleaned:
        return True

    if not re.match(r"^[A-Z0-9]{10,30}$", cleaned):
        return True

    return False


def add_issue(
    issues: list[dict[str, Any]],
    seen: set[tuple[str, str, str]],
    severity: str,
    field: str,
    message: str,
    value: Any = None,
):
    key = (severity, field, message)

    if key in seen:
        return

    seen.add(key)

    issues.append({
        "severity": severity,
        "field": field,
        "message": message,
        "value": value,
    })


def validate_fact(
    intelligence: dict[str, Any],
    field_path: str,
    issues: list[dict[str, Any]],
    seen: set[tuple[str, str, str]],
    critical: bool = False,
):
    fact = get_path(intelligence, field_path)

    if fact is None:
        add_issue(
            issues,
            seen,
            "ERROR" if critical else "WARN",
            field_path,
            "Missing field",
        )
        return

    if isinstance(fact, dict):
        confidence = fact.get("confidence")
        source = fact.get("source")
        validated = fact.get("validated")
        validated_by = fact.get("validated_by", [])

        if source is None:
            add_issue(issues, seen, "ERROR", field_path, "Missing primary source")

        if confidence is not None and confidence < MIN_CONFIDENCE:
            add_issue(
                issues,
                seen,
                "WARN" if not critical else "ERROR",
                field_path,
                f"Low confidence below {MIN_CONFIDENCE}",
                confidence,
            )

        if validated is False:
            add_issue(
                issues,
                seen,
                "WARN" if not critical else "ERROR",
                field_path,
                "Fact is not validated",
            )

        if critical and not validated_by:
            add_issue(
                issues,
                seen,
                "WARN",
                field_path,
                "Critical fact has no cross-document validation",
            )

        if critical and isinstance(validated_by, list) and len(validated_by) == 1:
            add_issue(
                issues,
                seen,
                "WARN",
                field_path,
                "Critical fact validated by only one source",
            )


def validate_metadata(
    intelligence: dict[str, Any],
    issues: list[dict[str, Any]],
    seen: set[tuple[str, str, str]],
):
    product_name = get_path(intelligence, "metadata.product_name")
    uin = get_path(intelligence, "metadata.uin")

    if not product_name:
        add_issue(issues, seen, "ERROR", "metadata.product_name", "Missing product name")

    if is_placeholder_uin(uin):
        add_issue(issues, seen, "ERROR", "metadata.uin", "Invalid or placeholder UIN", uin)


def validate_all_facts(
    intelligence: dict[str, Any],
    issues: list[dict[str, Any]],
    seen: set[tuple[str, str, str]],
):
    for section in ["waiting_periods", "core_benefits", "product_facts", "discounts", "optional_covers"]:
        items = intelligence.get(section, {})
        if not isinstance(items, dict):
            continue

        for key, fact in items.items():
            if isinstance(fact, dict):
                field_path = f"{section}.{key}"
                validate_fact(
                    intelligence,
                    field_path,
                    issues,
                    seen,
                    critical=field_path in CRITICAL_FIELDS,
                )


def validate_required_fields(
    intelligence: dict[str, Any],
    issues: list[dict[str, Any]],
    seen: set[tuple[str, str, str]],
):
    for field_path in CRITICAL_FIELDS:
        if field_path.startswith("metadata."):
            continue

        validate_fact(
            intelligence,
            field_path,
            issues,
            seen,
            critical=True,
        )


def detect_conflicts(
    intelligence: dict[str, Any],
    issues: list[dict[str, Any]],
    seen: set[tuple[str, str, str]],
):
    """
    Lightweight conflict detector.
    Currently detects contradictory numeric durations in waiting periods
    if future extractors add candidate_values.
    """
    waiting_periods = intelligence.get("waiting_periods", {})

    for field, fact in waiting_periods.items():
        if not isinstance(fact, dict):
            continue

        candidates = fact.get("candidate_values")
        if not candidates:
            continue

        unique_values = set(str(v) for v in candidates)
        if len(unique_values) > 1:
            add_issue(
                issues,
                seen,
                "ERROR",
                f"waiting_periods.{field}",
                "Conflicting candidate values detected",
                list(unique_values),
            )


def score_report(issues: list[dict[str, Any]]) -> tuple[int, str]:
    errors = sum(1 for i in issues if i["severity"] == "ERROR")
    warnings = sum(1 for i in issues if i["severity"] == "WARN")

    score = 100
    score -= errors * 15
    score -= warnings * 5
    score = max(score, 0)

    if errors:
        status = "FAIL"
    elif warnings:
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    return score, status


def validate(entity_id: str) -> dict[str, Any]:
    insurer_slug, product_slug = entity_id.split(":")

    input_path = (
        BASE_DIR
        / "knowledge"
        / "health"
        / insurer_slug
        / product_slug
        / "intelligence"
        / "product_intelligence.json"
    )

    if not input_path.exists():
        raise FileNotFoundError(f"Missing product intelligence file: {input_path}")

    intelligence = load_json(input_path)

    issues: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    validate_metadata(intelligence, issues, seen)
    validate_required_fields(intelligence, issues, seen)
    validate_all_facts(intelligence, issues, seen)
    detect_conflicts(intelligence, issues, seen)
    
    score, status = score_report(issues)

    report = {
        "entity_id": entity_id,
        "validator_version": VALIDATOR_VERSION,
        "input_file": str(input_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "score": score,
        "status": status,
        "issue_count": len(issues),
        "error_count": sum(1 for i in issues if i["severity"] == "ERROR"),
        "warning_count": sum(1 for i in issues if i["severity"] == "WARN"),
        "issues": issues,
    }

    out_dir = BASE_DIR / "knowledge" / "health" / insurer_slug / product_slug / "validation"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "product_intelligence_validation_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    report["output_file"] = str(out_path.relative_to(BASE_DIR)).replace("\\", "/")

    return report


def print_report(report: dict[str, Any]):
    print("=" * 70)
    print("PRODUCT INTELLIGENCE VALIDATOR")
    print("=" * 70)
    print(f"Entity   : {report['entity_id']}")
    print(f"Version  : {report['validator_version']}")
    print(f"Status   : {report['status']}")
    print(f"Score    : {report['score']}")
    print(f"Issues   : {report['issue_count']}")
    print(f"Errors   : {report['error_count']}")
    print(f"Warnings : {report['warning_count']}")
    print(f"Output   : {report['output_file']}")
    print("-" * 70)

    for issue in report["issues"]:
        print(f"[{issue['severity']}] {issue['field']}")
        print(f"  {issue['message']}")
        if issue.get("value") is not None:
            print(f"  value: {issue['value']}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity-id", required=True)
    args = parser.parse_args()

    report = validate(args.entity_id)
    print_report(report)


if __name__ == "__main__":
    main()