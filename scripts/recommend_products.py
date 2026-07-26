from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


RECOMMENDATION_VERSION = "0.1"


NEED_FIELD_MAP = {
    "maternity_or_newborn": [
        "core_benefits.delivery_newborn_cover",
    ],
    "wellness": [
        "core_benefits.wellness_program",
        "discounts.wellness_discount",
    ],
    "high_sum_insured": [
        "sum_insured_options.values",
    ],
    "low_waiting_period": [
        "waiting_periods.pre_existing_disease_waiting_period",
        "waiting_periods.initial_waiting_period",
        "waiting_periods.specified_disease_waiting_period",
    ],
}


PREFERENCE_FIELD_MAP = {
    "avoid_copay": [
        "product_facts.copay",
    ],
    "prefer_room_rent_no_limit": [
        "product_facts.room_rent_limit",
    ],
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_path(path_text: str) -> Path:
    path = Path(path_text)

    if path.is_absolute():
        return path

    return BASE_DIR / path


def quality_gate(comparison: dict[str, Any]) -> dict[str, Any]:
    warnings = comparison.get("quality_warnings", [])

    if warnings:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "One or more compared products have quality warnings.",
            "warnings": warnings,
        }

    return {
        "status": "PASS",
        "reason": "Compared products passed available quality gates.",
        "warnings": [],
    }


def product_names(comparison: dict[str, Any]) -> dict[str, str]:
    return {
        comparison["entity_a"]: comparison["product_a"]["product_name"],
        comparison["entity_b"]: comparison["product_b"]["product_name"],
    }


def find_missing_data_signal(
    comparison: dict[str, Any],
    field: str,
    need_or_preference: str,
) -> dict[str, Any] | None:
    names = product_names(comparison)

    for item in comparison.get("missing_data", []):
        if item.get("field") != field:
            continue

        available_for = item.get("available_for")
        missing_for = item.get("missing_for")

        return {
            "need": need_or_preference,
            "field": field,
            "favours": available_for,
            "favours_product_name": names.get(available_for),
            "against_or_unknown_for": missing_for,
            "against_or_unknown_product_name": names.get(missing_for),
            "reason": (
                f"{field} is available for {names.get(available_for, available_for)} "
                f"but not extracted for {names.get(missing_for, missing_for)}."
            ),
            "confidence": "medium",
            "evidence_type": "comparison_missing_data",
        }

    return None


def find_difference_signal(
    comparison: dict[str, Any],
    field: str,
    need_or_preference: str,
) -> dict[str, Any] | None:
    names = product_names(comparison)

    for item in comparison.get("differences", []):
        if item.get("field") != field:
            continue

        return {
            "need": need_or_preference,
            "field": field,
            "favours": None,
            "reason": (
                f"{field} differs between "
                f"{names.get(comparison['entity_a'], comparison['entity_a'])} and "
                f"{names.get(comparison['entity_b'], comparison['entity_b'])}. "
                "Advisor review required before interpreting this difference."
            ),
            "product_a_value": item.get("product_a_value"),
            "product_b_value": item.get("product_b_value"),
            "confidence": "low",
            "evidence_type": "comparison_difference",
        }

    return None


def build_signals(profile: dict[str, Any], comparison: dict[str, Any]) -> list[dict[str, Any]]:
    signals = []

    needs = profile.get("needs", {})
    preferences = profile.get("preferences", {})

    for need, enabled in needs.items():
        if not enabled:
            continue

        for field in NEED_FIELD_MAP.get(need, []):
            signal = find_missing_data_signal(comparison, field, need)
            if signal:
                signals.append(signal)
                continue

            signal = find_difference_signal(comparison, field, need)
            if signal:
                signals.append(signal)

    for preference, enabled in preferences.items():
        if not enabled:
            continue

        for field in PREFERENCE_FIELD_MAP.get(preference, []):
            signal = find_missing_data_signal(comparison, field, preference)
            if signal:
                signals.append(signal)
                continue

            signal = find_difference_signal(comparison, field, preference)
            if signal:
                signals.append(signal)

    return signals


def build_advisor_summary(
    profile: dict[str, Any],
    comparison: dict[str, Any],
    signals: list[dict[str, Any]],
    gate: dict[str, Any],
) -> list[str]:
    summary = []

    if signals:
        summary.append(
            f"{len(signals)} profile-relevant signal(s) were found from the comparison."
        )
    else:
        summary.append(
            "No strong profile-relevant product signals were found from the current comparison."
        )

    favoured = [s for s in signals if s.get("favours")]
    if favoured:
        product_counts: dict[str, int] = {}
        for signal in favoured:
            product = signal["favours"]
            product_counts[product] = product_counts.get(product, 0) + 1

        top_product = max(product_counts, key=product_counts.get)
        names = product_names(comparison)

        summary.append(
            f"{names.get(top_product, top_product)} has the strongest extracted signal count for this profile."
        )

    if gate["status"] != "PASS":
        summary.append(
            "Quality warnings are present, so this should be treated as advisor review input, not a final recommendation."
        )

    if comparison.get("missing_data"):
        summary.append(
            "Some comparison fields are missing. Improve extraction coverage before making a final recommendation."
        )

    return summary


def build_recommendation(
    signals: list[dict[str, Any]],
    gate: dict[str, Any],
) -> dict[str, Any]:
    if gate["status"] != "PASS":
        return {
            "status": "REVIEW_REQUIRED",
            "preferred_product": None,
            "reason": "Comparison quality is limited by validation or coverage warnings.",
        }

    favoured = [s for s in signals if s.get("favours")]

    if not favoured:
        return {
            "status": "NO_CLEAR_SIGNAL",
            "preferred_product": None,
            "reason": "No clear profile-relevant signal favours either product.",
        }

    product_counts: dict[str, int] = {}
    for signal in favoured:
        product = signal["favours"]
        product_counts[product] = product_counts.get(product, 0) + 1

    top_product = max(product_counts, key=product_counts.get)

    return {
        "status": "ADVISOR_REVIEW",
        "preferred_product": top_product,
        "reason": "Preferred product is based on signal count only and requires advisor review.",
        "signal_count": product_counts[top_product],
    }


def recommend(profile_path: str, comparison_path: str) -> dict[str, Any]:
    profile_file = normalize_path(profile_path)
    comparison_file = normalize_path(comparison_path)

    profile = load_json(profile_file)
    comparison = load_json(comparison_file)

    gate = quality_gate(comparison)
    signals = build_signals(profile, comparison)
    advisor_summary = build_advisor_summary(profile, comparison, signals, gate)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "recommendation_version": RECOMMENDATION_VERSION,
        "profile_id": profile.get("profile_id"),
        "profile": profile,
        "comparison_used": str(comparison_file.relative_to(BASE_DIR)).replace("\\", "/")
        if comparison_file.is_relative_to(BASE_DIR)
        else str(comparison_file),
        "entities": {
            "entity_a": comparison.get("entity_a"),
            "entity_b": comparison.get("entity_b"),
        },
        "quality_gate": gate,
        "signals": signals,
        "advisor_summary": advisor_summary,
        "recommendation": build_recommendation(signals, gate),
    }

    out_dir = BASE_DIR / "knowledge" / "health" / "recommendations"
    out_dir.mkdir(parents=True, exist_ok=True)

    profile_slug = profile.get("profile_id") or profile_file.stem
    comparison_slug = comparison_file.stem

    out_path = out_dir / f"{profile_slug}__{comparison_slug}_recommendation.json"
    out_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    report["output_file"] = str(out_path.relative_to(BASE_DIR)).replace("\\", "/")

    return report


def print_report(report: dict[str, Any]):
    print("=" * 70)
    print("PRODUCT RECOMMENDATION INTELLIGENCE")
    print("=" * 70)
    print(f"Version        : {report['recommendation_version']}")
    print(f"Profile        : {report['profile_id']}")
    print(f"Quality Gate   : {report['quality_gate']['status']}")
    print(f"Signals        : {len(report['signals'])}")
    print(f"Status         : {report['recommendation']['status']}")
    print(f"Preferred      : {report['recommendation']['preferred_product']}")
    print(f"Output         : {report['output_file']}")
    print("-" * 70)

    print("Advisor Summary:")
    for item in report["advisor_summary"]:
        print(f"  - {item}")

    print("-" * 70)

    print("Signals:")
    for signal in report["signals"]:
        print(f"  - {signal['need']} | {signal['field']}")
        print(f"    favours: {signal.get('favours')}")
        print(f"    reason : {signal.get('reason')}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--comparison", required=True)
    args = parser.parse_args()

    report = recommend(args.profile, args.comparison)
    print_report(report)


if __name__ == "__main__":
    main()