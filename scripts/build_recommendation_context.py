from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


CONTEXT_ENGINE_VERSION = "0.3"

RULES_DIR = BASE_DIR / "knowledge" / "recommendation_rules" / "health"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else BASE_DIR / path


def safe_relative(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return str(path)


def clamp_score(score: int, min_score: int = 0, max_score: int = 10) -> int:
    return max(min_score, min(score, max_score))


def impact_from_score(score: int) -> str:
    if score >= 8:
        return "high"
    if score >= 5:
        return "medium"
    return "low"

def confidence_from_activation(
    activation_strength: str,
    activation_sources: list[str],
) -> str:
    source_count = len(activation_sources)

    if activation_strength == "explicit" and source_count >= 4:
        return "very_high"

    if activation_strength == "explicit" and source_count >= 2:
        return "high"

    if activation_strength == "explicit":
        return "medium"

    if activation_strength == "implicit" and source_count >= 3:
        return "medium"

    if activation_strength == "implicit":
        return "low"

    return "unknown"

def recommendation_horizon(
    need_id: str,
    activation_strength: str,
    activation_sources: list[str],
    future_context: dict[str, Any],
) -> str:
    """
    Determine when this recommendation becomes important.
    """

    source_set = set(activation_sources)

    # Immediate needs
    if activation_strength == "explicit":
        return "immediate"

    if "existing_cover" in source_set:
        return "immediate"

    # Short-term needs
    if (
        need_id == "maternity_or_newborn"
        and future_context.get("family_expansion_probability") == "high"
    ):
        return "short_term"

    # Medium-term needs
    if (
        need_id == "high_sum_insured"
        and future_context.get("cover_upgrade_need_next_2_3_years") == "high"
    ):
        return "medium_term"

    # Long-term wellness type recommendations
    if need_id == "wellness":
        return "long_term"

    return "short_term"

def build_future_context(profile: dict[str, Any]) -> dict[str, Any]:
    life_stage = profile.get("life_stage")
    age = profile.get("age")
    family_members = profile.get("family_members", [])
    financial = profile.get("financial_profile", {})

    future = dict(profile.get("future_context", {}))

    if life_stage == "married_planning_family":
        future.setdefault("family_expansion_probability", "high")

    if isinstance(age, int) and age < 40:
        future.setdefault("income_growth_probability", "medium")

    if financial.get("existing_health_cover", 0) <= 500000:
        future.setdefault("cover_upgrade_need_next_2_3_years", "high")

    if len(family_members) >= 2:
        future.setdefault("family_floater_relevance", "high")

    return future

def load_rules() -> dict[str, Any]:
    files = {
        "base": "base_need_rules.json",
        "life_stage": "life_stage_rules.json",
        "geography": "geography_rules.json",
        "income": "income_rules.json",
        "existing_cover": "existing_cover_rules.json",
    }

    rules = {}

    for key, filename in files.items():
        path = RULES_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing recommendation rule file: {path}")
        rules[key] = load_json(path)

    return rules


def find_income_band(annual_income: int | float | None, income_rules: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    if annual_income is None:
        return None, None

    for band_id, band in income_rules.get("income_bands", {}).items():
        min_income = band.get("annual_income_min")
        max_income = band.get("annual_income_max")

        if min_income is not None and annual_income < min_income:
            continue

        if max_income is not None and annual_income > max_income:
            continue

        return band_id, band

    return None, None


def find_existing_cover_band(existing_cover: int | float | None, cover_rules: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    if existing_cover is None:
        return None, None

    for band_id, band in cover_rules.get("existing_cover_bands", {}).items():
        cover_min = band.get("cover_min")
        cover_max = band.get("cover_max")

        if cover_min is not None and existing_cover < cover_min:
            continue

        if cover_max is not None and existing_cover > cover_max:
            continue

        return band_id, band

    return None, None


def add_adjustments(
    scores: dict[str, dict[str, Any]],
    factor_type: str,
    factor_id: str | None,
    factor_rule: dict[str, Any] | None,
):
    if not factor_id or not factor_rule:
        return

    for need_id, adjustment in factor_rule.get("adjustments", {}).items():
        if need_id not in scores:
            continue

        delta = adjustment.get("score_delta", 0)

        scores[need_id]["raw_score"] += delta
        scores[need_id]["adjustments"].append(
            {
                "factor_type": factor_type,
                "factor_id": factor_id,
                "factor_display_name": factor_rule.get("display_name"),
                "score_delta": delta,
                "reason": adjustment.get("reason"),
                "customer_friendly_reason": adjustment.get("customer_friendly_reason"),
            }
        )


def build_context(profile_path: str) -> dict[str, Any]:
    profile_file = normalize_path(profile_path)
    profile = load_json(profile_file)

    if profile.get("domain") != "health":
        raise ValueError("Recommendation Context Engine v0.1 currently supports domain=health only.")

    rules = load_rules()
    base_rules = rules["base"]

    scores: dict[str, dict[str, Any]] = {}

    for need_id, need in base_rules.get("base_needs", {}).items():
        base_score = need.get("base_score", 0)

        scores[need_id] = {
            "need_id": need_id,
            "display_name": need.get("display_name"),
            "short_label": need.get("short_label"),
            "category": need.get("category"),
            "description": need.get("description"),
            "customer_friendly_description": need.get("customer_friendly_description"),
            "advisor_explanation": need.get("advisor_explanation"),
            "relevant_fields": need.get("relevant_fields", []),
            "related_needs": need.get("related_needs", []),
            "risk_caution": need.get("risk_caution"),
            "compliance_note": need.get("compliance_note"),
            "base_score": base_score,
            "raw_score": base_score,
            "adjustments": [],
        }

    life_stage = profile.get("life_stage")
    life_stage_rule = rules["life_stage"].get("life_stages", {}).get(life_stage)
    add_adjustments(scores, "life_stage", life_stage, life_stage_rule)

    city_tier = profile.get("location", {}).get("city_tier")
    geography_rule = rules["geography"].get("city_tiers", {}).get(city_tier)
    add_adjustments(scores, "geography", city_tier, geography_rule)

    financial = profile.get("financial_profile", {})

    annual_income = financial.get("annual_income")
    income_band_id, income_band_rule = find_income_band(annual_income, rules["income"])
    add_adjustments(scores, "income", income_band_id, income_band_rule)

    existing_cover = financial.get("existing_health_cover")
    cover_band_id, cover_band_rule = find_existing_cover_band(
        existing_cover,
        rules["existing_cover"],
    )
    add_adjustments(scores, "existing_cover", cover_band_id, cover_band_rule)

    active_needs = profile.get("needs", {})
    preferences = profile.get("preferences", {})

    derived_future_context = build_future_context(profile)

    need_scores = []

    for need_id, score in scores.items():
        raw_priority_score = score["raw_score"]
        normalized_priority_score = clamp_score(raw_priority_score)

        activation_sources = []

        if active_needs.get(need_id):
            activation_sources.append("explicit_need")

        if preferences.get(need_id):
            activation_sources.append("explicit_preference")

        if preferences.get("prefer_room_rent_no_limit") and need_id == "room_rent_flexibility":
            activation_sources.append("explicit_preference")

        for adjustment in score.get("adjustments", []):
            if adjustment.get("score_delta", 0) > 0:
                activation_sources.append(adjustment.get("factor_type"))

        activation_sources = sorted(set(activation_sources))

        if (
            active_needs.get(need_id)
            or preferences.get(need_id)
            or (
                preferences.get("prefer_room_rent_no_limit")
                and need_id == "room_rent_flexibility"
            )
        ):
            activation_strength = "explicit"
        elif activation_sources:
            activation_strength = "implicit"
        else:
            activation_strength = "inactive"

        enabled_by_profile = activation_strength in ["explicit", "implicit"]

        score["raw_priority_score"] = raw_priority_score
        score["normalized_priority_score"] = normalized_priority_score

        # Backward-compatible fields
        score["final_score"] = normalized_priority_score
        score["impact"] = impact_from_score(normalized_priority_score)
        score["enabled_by_profile"] = enabled_by_profile

        score["activation_sources"] = activation_sources
        score["activation_strength"] = activation_strength
        score["activation_evidence_count"] = len(activation_sources)
        score["need_confidence"] = confidence_from_activation(
            activation_strength,
            activation_sources,
        )

        score["recommendation_horizon"] = recommendation_horizon(
        need_id,
            activation_strength,
            activation_sources,
            derived_future_context,
         )

        need_scores.append(score)

    need_scores.sort(
        key=lambda item: (
            not item["enabled_by_profile"],
            -item["raw_priority_score"],
            -item["normalized_priority_score"],
            item["need_id"],
        )
    )
 
    context = {
        "generated_at": datetime.now(UTC).isoformat(),
        "context_engine_version": CONTEXT_ENGINE_VERSION,
        "profile_id": profile.get("profile_id"),
        "domain": profile.get("domain"),
        "profile": profile,
        "source_files": {
            "profile": safe_relative(profile_file),
            "rules_dir": safe_relative(RULES_DIR),
        },
        "matched_context": {
            "life_stage": life_stage,
            "city_tier": city_tier,
            "income_band": income_band_id,
            "existing_cover_band": cover_band_id,
        },
        "derived_future_context": derived_future_context,
        "need_scores": need_scores,
        "top_priorities": [
            {
                "need_id": item["need_id"],
                "display_name": item["display_name"],
                "raw_priority_score": item["raw_priority_score"],
                "normalized_priority_score": item["normalized_priority_score"],
                "final_score": item["final_score"],
                "impact": item["impact"],
                "activation_strength": item["activation_strength"],
                "activation_sources": item["activation_sources"],
                "need_confidence": item["need_confidence"],
                "activation_evidence_count": item["activation_evidence_count"],
                "recommendation_horizon": item["recommendation_horizon"],
            }
            for item in need_scores
            if item["enabled_by_profile"]
        ][:5],
    }

    out_dir = BASE_DIR / "knowledge" / "health" / "recommendation_contexts"
    out_dir.mkdir(parents=True, exist_ok=True)

    profile_slug = profile.get("profile_id") or profile_file.stem
    out_path = out_dir / f"{profile_slug}_recommendation_context.json"

    out_path.write_text(
        json.dumps(context, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    context["output_file"] = safe_relative(out_path)
    return context


def print_report(context: dict[str, Any]):
    print("=" * 70)
    print("RECOMMENDATION CONTEXT ENGINE")
    print("=" * 70)
    print(f"Version      : {context['context_engine_version']}")
    print(f"Profile      : {context['profile_id']}")
    print(f"Domain       : {context['domain']}")
    print(f"Life Stage   : {context['matched_context']['life_stage']}")
    print(f"City Tier    : {context['matched_context']['city_tier']}")
    print(f"Income Band  : {context['matched_context']['income_band']}")
    print(f"Cover Band   : {context['matched_context']['existing_cover_band']}")
    print(f"Output       : {context['output_file']}")
    print("-" * 70)

    print("Top Priorities:")
    for item in context["top_priorities"]:
        print(
            f"  - {item['display_name']}: "
            f"{item['normalized_priority_score']}/10 "
            f"raw={item['raw_priority_score']} "
            f"({item['impact']}, {item['activation_strength']}, "
            f"confidence={item['need_confidence']}, "
            f"horizon={item['recommendation_horizon']})"
        )

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()

    context = build_context(args.profile)
    print_report(context)


if __name__ == "__main__":
    main()