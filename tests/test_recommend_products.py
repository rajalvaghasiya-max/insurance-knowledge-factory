import json
from pathlib import Path

import pytest

from scripts import recommend_products


ENTITY_A = "insurer_a:product_a"
ENTITY_B = "insurer_b:product_b"


def base_profile() -> dict:
    return {
        "profile_id": "young_family",
        "needs": {
            "maternity_or_newborn": False,
            "wellness": False,
            "high_sum_insured": False,
            "low_waiting_period": False,
        },
        "preferences": {
            "avoid_copay": False,
            "prefer_room_rent_no_limit": False,
        },
    }


def base_comparison() -> dict:
    return {
        "entity_a": ENTITY_A,
        "entity_b": ENTITY_B,
        "product_a": {
            "product_name": "Product A",
        },
        "product_b": {
            "product_name": "Product B",
        },
        "quality_warnings": [],
        "missing_data": [],
        "differences": [],
    }


def write_json(base_dir: Path, relative_path: str, data: dict) -> Path:
    path = base_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def write_profile_and_comparison(
    base_dir: Path,
    *,
    profile: dict | None = None,
    comparison: dict | None = None,
) -> tuple[Path, Path]:
    profile_path = write_json(
        base_dir,
        "samples/customer_profiles/young_family.json",
        profile or base_profile(),
    )
    comparison_path = write_json(
        base_dir,
        "knowledge/health/comparisons/product_a_vs_product_b.json",
        comparison or base_comparison(),
    )
    return profile_path, comparison_path


@pytest.fixture
def isolated_base_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(recommend_products, "BASE_DIR", tmp_path)
    return tmp_path


def test_quality_gate_passes_when_comparison_has_no_quality_warnings():
    gate = recommend_products.quality_gate({"quality_warnings": []})

    assert gate == {
        "status": "PASS",
        "reason": "Compared products passed available quality gates.",
        "warnings": [],
    }


def test_quality_gate_requires_review_when_comparison_has_quality_warnings():
    warnings = [
        {
            "entity_id": ENTITY_A,
            "message": "Coverage below target",
        }
    ]

    gate = recommend_products.quality_gate({"quality_warnings": warnings})

    assert gate == {
        "status": "REVIEW_REQUIRED",
        "reason": "One or more compared products have quality warnings.",
        "warnings": warnings,
    }


def test_profile_need_creates_signal_from_comparison_missing_data(isolated_base_dir):
    profile = base_profile()
    profile["needs"]["maternity_or_newborn"] = True
    comparison = base_comparison()
    comparison["missing_data"] = [
        {
            "field": "core_benefits.delivery_newborn_cover",
            "available_for": ENTITY_B,
            "missing_for": ENTITY_A,
        }
    ]
    profile_path, comparison_path = write_profile_and_comparison(
        isolated_base_dir,
        profile=profile,
        comparison=comparison,
    )

    report = recommend_products.recommend(str(profile_path), str(comparison_path))

    assert report["signals"] == [
        {
            "need": "maternity_or_newborn",
            "field": "core_benefits.delivery_newborn_cover",
            "favours": ENTITY_B,
            "favours_product_name": "Product B",
            "against_or_unknown_for": ENTITY_A,
            "against_or_unknown_product_name": "Product A",
            "reason": (
                "core_benefits.delivery_newborn_cover is available for Product B "
                "but not extracted for Product A."
            ),
            "confidence": "medium",
            "evidence_type": "comparison_missing_data",
        }
    ]
    assert report["recommendation"]["status"] == "ADVISOR_REVIEW"
    assert report["recommendation"]["preferred_product"] == ENTITY_B


def test_recommendation_stays_review_required_when_quality_gate_fails(
    isolated_base_dir,
):
    profile = base_profile()
    profile["needs"]["maternity_or_newborn"] = True
    comparison = base_comparison()
    comparison["quality_warnings"] = [
        {
            "entity_id": ENTITY_A,
            "message": "Validation warning",
        }
    ]
    comparison["missing_data"] = [
        {
            "field": "core_benefits.delivery_newborn_cover",
            "available_for": ENTITY_B,
            "missing_for": ENTITY_A,
        }
    ]
    profile_path, comparison_path = write_profile_and_comparison(
        isolated_base_dir,
        profile=profile,
        comparison=comparison,
    )

    report = recommend_products.recommend(str(profile_path), str(comparison_path))

    assert report["quality_gate"]["status"] == "REVIEW_REQUIRED"
    assert len(report["signals"]) == 1
    assert report["recommendation"] == {
        "status": "REVIEW_REQUIRED",
        "preferred_product": None,
        "reason": "Comparison quality is limited by validation or coverage warnings.",
    }


def test_recommendation_returns_no_clear_signal_when_no_relevant_signals_exist(
    isolated_base_dir,
):
    profile_path, comparison_path = write_profile_and_comparison(isolated_base_dir)

    report = recommend_products.recommend(str(profile_path), str(comparison_path))

    assert report["quality_gate"]["status"] == "PASS"
    assert report["signals"] == []
    assert report["recommendation"] == {
        "status": "NO_CLEAR_SIGNAL",
        "preferred_product": None,
        "reason": "No clear profile-relevant signal favours either product.",
    }


def test_recommendation_output_json_is_written_correctly(isolated_base_dir):
    profile = base_profile()
    profile["needs"]["high_sum_insured"] = True
    comparison = base_comparison()
    comparison["missing_data"] = [
        {
            "field": "sum_insured_options.values",
            "available_for": ENTITY_A,
            "missing_for": ENTITY_B,
        }
    ]
    profile_path, comparison_path = write_profile_and_comparison(
        isolated_base_dir,
        profile=profile,
        comparison=comparison,
    )

    report = recommend_products.recommend(str(profile_path), str(comparison_path))

    assert report["output_file"] == (
        "knowledge/health/recommendations/"
        "young_family__product_a_vs_product_b_recommendation.json"
    )
    output_path = isolated_base_dir / report["output_file"]
    saved_report = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved_report["profile_id"] == "young_family"
    assert saved_report["quality_gate"]["status"] == "PASS"
    assert saved_report["recommendation"]["preferred_product"] == ENTITY_A
    assert saved_report["comparison_used"] == (
        "knowledge/health/comparisons/product_a_vs_product_b.json"
    )
