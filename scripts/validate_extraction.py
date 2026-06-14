from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_waiting_period(intelligence: dict[str, Any], fact_type: str) -> dict[str, Any] | None:
    for item in intelligence.get("waiting_periods", []):
        if item.get("type") == fact_type:
            return item
    return None


def validate(entity_id: str) -> dict[str, Any]:
    insurer_slug, product_slug = entity_id.split(":")

    intelligence_path = (
        BASE_DIR
        / "knowledge"
        / "health"
        / insurer_slug
        / product_slug
        / "intelligence"
        / "policy_intelligence.json"
    )

    expected_path = (
        BASE_DIR
        / "knowledge"
        / "health"
        / "validations"
        / f"{entity_id.replace(':', '_')}_expected.json"
    )

    if not intelligence_path.exists():
        raise FileNotFoundError(f"Missing intelligence file: {intelligence_path}")

    if not expected_path.exists():
        raise FileNotFoundError(f"Missing expected validation file: {expected_path}")

    intelligence = load_json(intelligence_path)
    expected = load_json(expected_path)

    results = []

    # Metadata
    for key, expected_value in expected.get("metadata", {}).items():
        actual_value = intelligence.get("metadata", {}).get(key)
        results.append({
            "category": "metadata",
            "field": key,
            "expected": expected_value,
            "actual": actual_value,
            "passed": actual_value == expected_value,
        })

    # Waiting periods
    for field, expected_value in expected.get("waiting_periods", {}).items():
        fact = get_waiting_period(intelligence, field)

        if fact is None:
            actual_value = None
        elif "duration_months" in fact:
            actual_value = fact.get("duration_months")
        elif "duration_days" in fact:
            actual_value = fact.get("duration_days")
        else:
            actual_value = None

        results.append({
            "category": "waiting_periods",
            "field": field,
            "expected": expected_value,
            "actual": actual_value,
            "passed": actual_value == expected_value,
        })

    # Product facts
    for field, expected_value in expected.get("product_facts", {}).items():
        fact = intelligence.get("product_facts", {}).get(field)
        actual_value = fact.get("value") if fact else None

        results.append({
            "category": "product_facts",
            "field": field,
            "expected": expected_value,
            "actual": actual_value,
            "passed": actual_value == expected_value,
        })

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    score = round((passed / total) * 100, 2) if total else 0

    report = {
        "entity_id": entity_id,
        "validator_version": "0.1",
        "intelligence_file": str(intelligence_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "expected_file": str(expected_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "score": score,
        "passed": passed,
        "total": total,
        "status": "PASS" if score == 100 else "FAIL",
        "results": results,
    }

    output_dir = BASE_DIR / "knowledge" / "health" / "validation_reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{entity_id.replace(':', '_')}_validation_report.json"
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    return report


def print_report(report: dict[str, Any]) -> None:
    print("=" * 70)
    print("EXTRACTION VALIDATION")
    print("=" * 70)
    print(f"Entity : {report['entity_id']}")
    print(f"Score  : {report['score']}%")
    print(f"Status : {report['status']}")
    print(f"Passed : {report['passed']} / {report['total']}")
    print("-" * 70)

    for item in report["results"]:
        symbol = "✓" if item["passed"] else "✗"
        print(f"{symbol} [{item['category']}] {item['field']}")
        print(f"    expected: {item['expected']}")
        print(f"    actual  : {item['actual']}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity-id", required=True)
    args = parser.parse_args()

    report = validate(args.entity_id)
    print_report(report)


if __name__ == "__main__":
    main()