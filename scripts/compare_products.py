from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


COMPARISON_VERSION = "0.3.1"


SECTIONS_TO_COMPARE = [
    "eligibility",
    "sum_insured_options",
    "waiting_periods",
    "product_facts",
    "core_benefits",
    "discounts",
    "optional_covers",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def entity_path(entity_id: str) -> tuple[str, str]:
    insurer_slug, product_slug = entity_id.split(":")
    return insurer_slug, product_slug


def load_product_intelligence(entity_id: str) -> dict[str, Any]:
    insurer_slug, product_slug = entity_path(entity_id)

    path = (
        BASE_DIR
        / "knowledge"
        / "health"
        / insurer_slug
        / product_slug
        / "intelligence"
        / "product_intelligence.json"
    )

    if not path.exists():
        raise FileNotFoundError(f"Missing product intelligence file: {path}")

    data = load_json(path)
    data["_source_file"] = str(path.relative_to(BASE_DIR)).replace("\\", "/")
    return data


def load_validation_report(entity_id: str) -> dict[str, Any] | None:
    insurer_slug, product_slug = entity_path(entity_id)

    path = (
        BASE_DIR
        / "knowledge"
        / "health"
        / insurer_slug
        / product_slug
        / "validation"
        / "product_intelligence_validation_report.json"
    )

    if not path.exists():
        return None

    data = load_json(path)
    data["_source_file"] = str(path.relative_to(BASE_DIR)).replace("\\", "/")
    return data


def load_coverage_report(entity_id: str) -> dict[str, Any] | None:
    insurer_slug, product_slug = entity_path(entity_id)

    path = (
        BASE_DIR
        / "knowledge"
        / "health"
        / insurer_slug
        / product_slug
        / "coverage"
        / "product_coverage_report.json"
    )

    if not path.exists():
        return None

    data = load_json(path)
    data["_source_file"] = str(path.relative_to(BASE_DIR)).replace("\\", "/")
    return data


TECHNICAL_KEYS_TO_IGNORE = {
    "source",
    "source_file",
    "source_type",
    "page_number",
    "confidence",
    "validated",
    "validated_by",
    "raw_text",
    "raw_terms",
}

ADVISOR_FIELDS_TO_HIDE = {
    "sum_insured_options.values_raw",
}

def fact_value(value: Any) -> Any:
    if isinstance(value, dict):
        if "value" in value:
            return value.get("value")
        if "duration_months" in value:
            return f"{value.get('duration_months')} months"
        if "duration_days" in value:
            return f"{value.get('duration_days')} days"
        if "values" in value:
            return value.get("values")

    return value


def flatten_section(section: Any, prefix: str = "") -> dict[str, Any]:
    """
    M4 v0.2

    Business comparison flattening.

    Compare:
    - value
    - values
    - duration_months
    - duration_days
    - booleans / simple strings

    Ignore technical/provenance fields:
    - source
    - confidence
    - validated
    - validated_by
    - raw_text
    """

    flat = {}

    if not isinstance(section, dict):
        return flat

    for key, value in section.items():
        if key in TECHNICAL_KEYS_TO_IGNORE:
            continue

        field = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            if any(
                marker in value
                for marker in [
                    "value",
                    "duration_months",
                    "duration_days",
                    "values",
                ]
            ):
                flat[field] = fact_value(value)
            else:
                nested = flatten_section(value, field)
                if nested:
                    flat.update(nested)

        else:
            flat[field] = value

    return flat


def compare_sections(
    product_a: dict[str, Any],
    product_b: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    differences = []
    missing_data = []

    for section in SECTIONS_TO_COMPARE:
        flat_a = flatten_section(product_a.get(section, {}))
        flat_b = flatten_section(product_b.get(section, {}))

        all_fields = sorted(set(flat_a) | set(flat_b))

        for field in all_fields:
            value_a = flat_a.get(field)
            value_b = flat_b.get(field)

            full_field = f"{section}.{field}"

            if value_a in [None, "", [], {}] and value_b not in [None, "", [], {}]:
                missing_data.append(
                    {
                        "field": full_field,
                        "missing_for": product_a.get("entity_id"),
                        "available_for": product_b.get("entity_id"),
                        "available_value": value_b,
                    }
                )
                continue

            if value_b in [None, "", [], {}] and value_a not in [None, "", [], {}]:
                missing_data.append(
                    {
                        "field": full_field,
                        "missing_for": product_b.get("entity_id"),
                        "available_for": product_a.get("entity_id"),
                        "available_value": value_a,
                    }
                )
                continue

            if value_a != value_b:
                differences.append(
                    {
                        "field": full_field,
                        "product_a_value": value_a,
                        "product_b_value": value_b,
                    }
                )

    return differences, missing_data


def build_quality_summary(
    entity_id: str,
    validation: dict[str, Any] | None,
    coverage: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "entity_id": entity_id,
        "validation_status": validation.get("status") if validation else None,
        "validation_score": validation.get("score") if validation else None,
        "coverage_status": coverage.get("coverage_status") if coverage else None,
        "coverage_score": coverage.get("overall_coverage") if coverage else None,
        "validation_file": validation.get("_source_file") if validation else None,
        "coverage_file": coverage.get("_source_file") if coverage else None,
    }


def build_quality_warnings(quality_a: dict[str, Any], quality_b: dict[str, Any]) -> list[str]:
    warnings = []

    for quality in [quality_a, quality_b]:
        entity_id = quality["entity_id"]

        if quality["validation_status"] not in ["PASS", None]:
            warnings.append(
                f"{entity_id} validation status is {quality['validation_status']}."
            )

        if quality["coverage_status"] not in ["READY", None]:
            warnings.append(
                f"{entity_id} coverage status is {quality['coverage_status']}."
            )

    return warnings


def build_winner_signals(
    entity_a: str,
    entity_b: str,
    differences: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    v0.1 intentionally avoids advice/ranking.

    Winner signals are limited to objective field-level signals where lower/higher
    is obviously comparable. Full recommendation logic comes later.
    """
    signals = []

    for diff in differences:
        field = diff["field"]
        a = diff["product_a_value"]
        b = diff["product_b_value"]

        if field.endswith("waiting_periods.pre_existing_disease_waiting_period"):
            signals.append(
                {
                    "field": field,
                    "signal_type": "waiting_period_difference",
                    "note": "Lower PED waiting period is generally preferable, but suitability depends on customer context.",
                    "product_a": entity_a,
                    "product_a_value": a,
                    "product_b": entity_b,
                    "product_b_value": b,
                }
            )

    return signals


def build_recommendations(
    missing_data: list[dict[str, Any]],
    quality_warnings: list[str],
) -> list[str]:
    recommendations = []

    if quality_warnings:
        recommendations.append(
            "Resolve quality warnings before using this comparison in advisor-facing workflows."
        )

    if missing_data:
        recommendations.append(
            "Comparison has missing fields. Improve product extraction before relying on differences."
        )

    if not quality_warnings and not missing_data:
        recommendations.append(
            "Comparison is ready for review. Use only as evidence-backed product intelligence, not final advice."
        )

    return recommendations

DISPLAY_LABELS = {
    "eligibility.adult_entry_age": "Adult Entry Age",
    "eligibility.dependent_child_entry_age": "Dependent Child Entry Age",
    "sum_insured_options.values": "Sum Insured Options",

    "waiting_periods.pre_existing_disease_waiting_period": "Pre-existing Disease Waiting Period",
    "waiting_periods.specified_disease_waiting_period": "Specified Disease Waiting Period",
    "waiting_periods.initial_waiting_period": "Initial Waiting Period",
    "waiting_periods.delivery_newborn_waiting_period": "Delivery / Newborn Waiting Period",
    "waiting_periods.bariatric_surgery_waiting_period": "Bariatric Surgery Waiting Period",

    "product_facts.copay": "Co-pay",
    "product_facts.room_rent_limit": "Room Rent Limit",

    "core_benefits.delivery_newborn_cover": "Delivery & Newborn Cover",
    "core_benefits.wellness_program": "Wellness Program",
    "core_benefits.air_ambulance": "Air Ambulance",
    "core_benefits.hospital_cash": "Hospital Cash",
    "core_benefits.automatic_restoration": "Automatic Restoration",
    "core_benefits.bariatric_surgery": "Bariatric Surgery",

    "discounts.long_term_discount": "Long-term Discount",
    "discounts.wellness_discount": "Wellness Discount",
    "discounts.online_discount": "Online Discount",

    "optional_covers.buy_back_ped_waiting_period": "Buy-back PED Waiting Period",
}


ADVISOR_GROUPS = {
    "eligibility": "Eligibility",
    "sum_insured_options": "Sum Insured",
    "waiting_periods": "Waiting Periods",
    "product_facts": "Important Policy Conditions",
    "core_benefits": "Core Benefits",
    "discounts": "Discounts",
    "optional_covers": "Optional Covers",
}


def display_label(field: str) -> str:
    return DISPLAY_LABELS.get(field, field.replace("_", " ").replace(".", " > ").title())


def advisor_group(field: str) -> str:
    section = field.split(".", 1)[0]
    return ADVISOR_GROUPS.get(section, "Other")


def format_value(value: Any) -> Any:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)

    if value is True:
        return "Available"

    if value is False:
        return "Not Available"

    if value in [None, "", [], {}]:
        return "Not Extracted"

    return value


def build_advisor_view(
    entity_a: str,
    entity_b: str,
    product_a: dict[str, Any],
    product_b: dict[str, Any],
    differences: list[dict[str, Any]],
    missing_data: list[dict[str, Any]],
) -> dict[str, Any]:
    advisor_rows_by_group: dict[str, list[dict[str, Any]]] = {}

    for diff in differences:
        field = diff["field"]

        if field in ADVISOR_FIELDS_TO_HIDE:
            continue

            group = advisor_group(field)

        advisor_rows_by_group.setdefault(group, []).append(
            {
                "field": field,
                "label": display_label(field),
                "product_a_value": format_value(diff.get("product_a_value")),
                "product_b_value": format_value(diff.get("product_b_value")),
                "comparison_type": "different",
            }
        )

    for item in missing_data:
        field = item["field"]

        if field in ADVISOR_FIELDS_TO_HIDE:
            continue

        group = advisor_group(field)

        product_a_value = "Not Extracted"
        product_b_value = "Not Extracted"

        if item["missing_for"] == entity_a:
            product_a_value = "Not Extracted"
            product_b_value = format_value(item.get("available_value"))
        elif item["missing_for"] == entity_b:
            product_a_value = format_value(item.get("available_value"))
            product_b_value = "Not Extracted"

        advisor_rows_by_group.setdefault(group, []).append(
            {
                "field": field,
                "label": display_label(field),
                "product_a_value": product_a_value,
                "product_b_value": product_b_value,
                "comparison_type": "missing_data",
            }
        )

    return {
        "product_identity": {
            "product_a": {
                "entity_id": entity_a,
                "product_name": product_a.get("metadata", {}).get("product_name"),
                "uin": product_a.get("metadata", {}).get("uin"),
            },
            "product_b": {
                "entity_id": entity_b,
                "product_name": product_b.get("metadata", {}).get("product_name"),
                "uin": product_b.get("metadata", {}).get("uin"),
            },
        },
        "groups": [
            {
                "group": group,
                "items": items,
            }
            for group, items in advisor_rows_by_group.items()
        ],
    }

def compare_products(entity_a: str, entity_b: str) -> dict[str, Any]:
    product_a = load_product_intelligence(entity_a)
    product_b = load_product_intelligence(entity_b)

    validation_a = load_validation_report(entity_a)
    validation_b = load_validation_report(entity_b)

    coverage_a = load_coverage_report(entity_a)
    coverage_b = load_coverage_report(entity_b)

    differences, missing_data = compare_sections(product_a, product_b)

    quality_a = build_quality_summary(entity_a, validation_a, coverage_a)
    quality_b = build_quality_summary(entity_b, validation_b, coverage_b)

    quality_warnings = build_quality_warnings(quality_a, quality_b)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "comparison_version": COMPARISON_VERSION,
        "entity_a": entity_a,
        "entity_b": entity_b,
        "product_a": {
            "entity_id": entity_a,
            "product_name": product_a.get("metadata", {}).get("product_name"),
            "uin": product_a.get("metadata", {}).get("uin"),
            "source_file": product_a.get("_source_file"),
        },
        "product_b": {
            "entity_id": entity_b,
            "product_name": product_b.get("metadata", {}).get("product_name"),
            "uin": product_b.get("metadata", {}).get("uin"),
            "source_file": product_b.get("_source_file"),
        },
        "quality": {
            "product_a": quality_a,
            "product_b": quality_b,
        },
        "summary": {
            "difference_count": len(differences),
            "missing_data_count": len(missing_data),
            "quality_warning_count": len(quality_warnings),
        },
        "differences": differences,
        "missing_data": missing_data,
        "quality_warnings": quality_warnings,
        "winner_signals": build_winner_signals(entity_a, entity_b, differences),
        "advisor_view": build_advisor_view(
            entity_a,
            entity_b,
            product_a,
            product_b,
            differences,
            missing_data,
        ),
        "recommendations": build_recommendations(missing_data, quality_warnings),
    }

    out_dir = BASE_DIR / "knowledge" / "health" / "comparisons"
    out_dir.mkdir(parents=True, exist_ok=True)

    file_slug = (
        f"{entity_a.replace(':', '_')}__vs__{entity_b.replace(':', '_')}"
        "_comparison.json"
    )

    out_path = out_dir / file_slug
    out_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    report["output_file"] = str(out_path.relative_to(BASE_DIR)).replace("\\", "/")

    return report


def print_report(report: dict[str, Any]):
    print("=" * 70)
    print("PRODUCT COMPARISON")
    print("=" * 70)
    print(f"Version     : {report['comparison_version']}")
    print(f"Product A   : {report['product_a']['product_name']} ({report['entity_a']})")
    print(f"Product B   : {report['product_b']['product_name']} ({report['entity_b']})")
    print(f"Differences : {report['summary']['difference_count']}")
    print(f"Missing     : {report['summary']['missing_data_count']}")
    print(f"Warnings    : {report['summary']['quality_warning_count']}")
    print(f"Output      : {report['output_file']}")
    print("-" * 70)

    print("Quality Warnings:")
    if report["quality_warnings"]:
        for warning in report["quality_warnings"]:
            print(f"  - {warning}")
    else:
        print("  None")

    print("-" * 70)

    print("Top Differences:")
    for diff in report["differences"][:15]:
        print(f"  - {diff['field']}")
        print(f"    A: {diff['product_a_value']}")
        print(f"    B: {diff['product_b_value']}")

    print("-" * 70)

    print("Missing Data:")
    if report["missing_data"]:
        for item in report["missing_data"][:15]:
            print(
                f"  - {item['field']} missing for {item['missing_for']} "
                f"(available in {item['available_for']})"
            )
    else:
        print("  None")

    print("-" * 70)

    print("Recommendations:")
    for rec in report["recommendations"]:
        print(f"  - {rec}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity-a", required=True)
    parser.add_argument("--entity-b", required=True)
    args = parser.parse_args()

    report = compare_products(args.entity_a, args.entity_b)
    print_report(report)


if __name__ == "__main__":
    main()