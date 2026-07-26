from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


EXPLANATION_OBJECT_VERSION = "1.0"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return BASE_DIR / path


def safe_relative(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return str(path)


def importance_to_impact(score: int | None) -> str:
    if score is None:
        return "unknown"
    if score >= 8:
        return "high"
    if score >= 5:
        return "medium"
    return "low"


def build_unit_title(signal: dict[str, Any]) -> str:
    field = signal.get("field", "")
    need = signal.get("need", "")

    labels = {
        "core_benefits.delivery_newborn_cover": "Maternity & Newborn Relevance",
        "core_benefits.wellness_program": "Wellness Relevance",
        "discounts.wellness_discount": "Wellness Discount Relevance",
        "sum_insured_options.values": "Sum Insured Relevance",
        "waiting_periods.pre_existing_disease_waiting_period": "PED Waiting Period Relevance",
        "waiting_periods.initial_waiting_period": "Initial Waiting Period Relevance",
        "waiting_periods.specified_disease_waiting_period": "Specified Disease Waiting Period Relevance",
        "product_facts.copay": "Co-pay Relevance",
        "product_facts.room_rent_limit": "Room Rent Relevance",
    }

    return labels.get(field, need.replace("_", " ").title())


def build_explanation_text(signal: dict[str, Any]) -> str:
    favours_name = signal.get("favours_product_name") or signal.get("favours")
    unknown_name = signal.get("against_or_unknown_product_name") or signal.get(
        "against_or_unknown_for"
    )
    field = signal.get("field")
    need = signal.get("need")

    if signal.get("evidence_type") == "comparison_missing_data":
        return (
            f"For the profile need '{need}', the comparison found usable information "
            f"for {favours_name} on '{field}', while equivalent information was not "
            f"extracted for {unknown_name}."
        )

    if signal.get("evidence_type") == "comparison_difference":
        return (
            f"For the profile need '{need}', the compared products show a difference "
            f"on '{field}'. Advisor review is required before interpreting this signal."
        )

    return signal.get("reason") or "Explanation generated from recommendation signal."


def build_caution(signal: dict[str, Any], recommendation: dict[str, Any]) -> list[str]:
    cautions = []

    if signal.get("evidence_type") == "comparison_missing_data":
        cautions.append(
            "This signal is based on missing comparison data for one product, not confirmed absence of the benefit."
        )

    if recommendation.get("quality_gate", {}).get("status") != "PASS":
        cautions.append(
            "Quality gate is not PASS, so this explanation should be treated as review input."
        )

    return cautions


def build_explanation_units(
    recommendation: dict[str, Any],
) -> list[dict[str, Any]]:
    units = []

    for signal in recommendation.get("signals", []):
        importance_score = signal.get("importance_score")

        unit = {
            "unit_id": f"{signal.get('need')}::{signal.get('field')}",
            "title": build_unit_title(signal),
            "need": signal.get("need"),
            "field": signal.get("field"),
            "favours": signal.get("favours"),
            "favours_product_name": signal.get("favours_product_name"),
            "against_or_unknown_for": signal.get("against_or_unknown_for"),
            "against_or_unknown_product_name": signal.get(
                "against_or_unknown_product_name"
            ),
            "importance_score": importance_score,
            "impact": importance_to_impact(importance_score),
            "confidence": signal.get("confidence"),
            "evidence_type": signal.get("evidence_type"),
            "evidence_summary": signal.get("reason"),
            "explanation": build_explanation_text(signal),
            "cautions": build_caution(signal, recommendation),
            "source_signal": signal,
        }

        units.append(unit)

    return units


def build_risk_cautions(
    recommendation: dict[str, Any],
    comparison: dict[str, Any],
) -> list[str]:
    cautions = []

    gate = recommendation.get("quality_gate", {})
    if gate.get("status") != "PASS":
        cautions.append(
            "Recommendation quality gate is not PASS. Do not use as final advice without review."
        )

    if comparison.get("missing_data"):
        cautions.append(
            "Comparison contains missing data. Missing data should not be interpreted as benefit absence."
        )

    if comparison.get("quality_warnings"):
        cautions.append(
            "One or more products have validation or coverage warnings."
        )

    if recommendation.get("recommendation", {}).get("preferred_product") is None:
        cautions.append(
            "No final preferred product was selected by the recommendation engine."
        )

    return cautions


def build_followup_context(
    recommendation: dict[str, Any],
    comparison: dict[str, Any],
) -> dict[str, Any]:
    fields = set()

    for signal in recommendation.get("signals", []):
        if signal.get("field"):
            fields.add(signal["field"])

    for item in comparison.get("missing_data", []):
        if item.get("field"):
            fields.add(item["field"])

    return {
        "can_answer_followups": True,
        "recommended_sources": [
            "product_intelligence",
            "comparison_report",
            "recommendation_report",
            "evidence_router",
        ],
        "known_relevant_fields": sorted(fields),
        "allowed_followup_topics": [
            "eligibility",
            "sum_insured",
            "waiting_periods",
            "copay",
            "room_rent",
            "benefits",
            "discounts",
            "optional_covers",
            "claims",
            "exclusions",
        ],
        "principle": (
            "Channel summaries are views only. Follow-up answers should use the full "
            "knowledge base and evidence, not only pre-rendered summaries."
        ),
    }


def build_explanation_object(
    profile_path: str,
    recommendation_path: str,
    comparison_path: str,
) -> dict[str, Any]:
    profile_file = normalize_path(profile_path)
    recommendation_file = normalize_path(recommendation_path)
    comparison_file = normalize_path(comparison_path)

    profile = load_json(profile_file)
    recommendation = load_json(recommendation_file)
    comparison = load_json(comparison_file)

    explanation_units = build_explanation_units(recommendation)

    explanation = {
        "generated_at": datetime.now(UTC).isoformat(),
        "explanation_object_version": EXPLANATION_OBJECT_VERSION,
        "profile_id": profile.get("profile_id"),
        "profile_context": profile,
        "source_files": {
            "profile": safe_relative(profile_file),
            "recommendation": safe_relative(recommendation_file),
            "comparison": safe_relative(comparison_file),
        },
        "product_identity": {
            "product_a": comparison.get("product_a"),
            "product_b": comparison.get("product_b"),
        },
        "quality_gate": recommendation.get("quality_gate"),
        "recommendation_status": recommendation.get("recommendation", {}).get("status"),
        "preferred_product": recommendation.get("recommendation", {}).get(
            "preferred_product"
        ),
        "explanation_units": explanation_units,
        "risk_cautions": build_risk_cautions(recommendation, comparison),
        "followup_context": build_followup_context(recommendation, comparison),
        "channel_renderers_pending": [
            "advisor_talking_points",
            "customer_summary",
            "sales_enablement_points",
            "api_summary",
        ],
    }

    out_dir = BASE_DIR / "knowledge" / "health" / "explanations"
    out_dir.mkdir(parents=True, exist_ok=True)

    profile_slug = profile.get("profile_id") or profile_file.stem
    comparison_slug = comparison_file.stem

    out_path = out_dir / f"{profile_slug}__{comparison_slug}_explanation.json"
    out_path.write_text(
        json.dumps(explanation, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    explanation["output_file"] = safe_relative(out_path)

    return explanation


def print_report(report: dict[str, Any]):
    print("=" * 70)
    print("CORE EXPLANATION OBJECT")
    print("=" * 70)
    print(f"Version        : {report['explanation_object_version']}")
    print(f"Profile        : {report['profile_id']}")
    print(f"Quality Gate   : {report['quality_gate']['status']}")
    print(f"Status         : {report['recommendation_status']}")
    print(f"Preferred      : {report['preferred_product']}")
    print(f"Units          : {len(report['explanation_units'])}")
    print(f"Cautions       : {len(report['risk_cautions'])}")
    print(f"Output         : {report['output_file']}")
    print("-" * 70)

    print("Explanation Units:")
    for unit in report["explanation_units"]:
        print(f"  - {unit['title']} | impact={unit['impact']} | confidence={unit['confidence']}")
        print(f"    favours: {unit.get('favours_product_name') or unit.get('favours')}")

    print("-" * 70)

    print("Risk Cautions:")
    for caution in report["risk_cautions"]:
        print(f"  - {caution}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--recommendation", required=True)
    parser.add_argument("--comparison", required=True)
    args = parser.parse_args()

    report = build_explanation_object(
        profile_path=args.profile,
        recommendation_path=args.recommendation,
        comparison_path=args.comparison,
    )
    print_report(report)


if __name__ == "__main__":
    main()