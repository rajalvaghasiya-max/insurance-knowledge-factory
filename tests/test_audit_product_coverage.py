import json
from pathlib import Path

import pytest

from scripts import audit_product_coverage


ENTITY_ID = "test_insurer:test_product"


def complete_product_intelligence() -> dict:
    return {
        "metadata": {
            "product_name": "Test Health Plan",
            "uin": "ABC1234567V01",
        },
        "eligibility": {
            "adult_entry_age": "18 years",
            "dependent_child_entry_age": "91 days",
        },
        "sum_insured_options": {
            "values": ["500000", "1000000"],
        },
        "waiting_periods": {
            "pre_existing_disease_waiting_period": "36 months",
            "specified_disease_waiting_period": "24 months",
            "initial_waiting_period": "30 days",
            "delivery_newborn_waiting_period": "24 months",
            "bariatric_surgery_waiting_period": "24 months",
        },
        "product_facts": {
            "copay": "No copay",
            "room_rent_limit": "Single private room",
        },
        "core_benefits": {
            "in_patient_treatment": "Covered",
            "day_care_treatment": "Covered",
            "ayush_treatment": "Covered",
            "pre_hospitalization": "60 days",
            "post_hospitalization": "90 days",
            "domiciliary_hospitalization": "Covered",
            "home_care_treatment": "Covered",
            "road_ambulance": "Covered",
            "air_ambulance": "Covered",
            "organ_donor_expenses": "Covered",
            "automatic_restoration": "Covered",
            "delivery_newborn_cover": "Covered",
            "bariatric_surgery": "Covered",
            "hospital_cash": "Covered",
            "wellness_program": "Covered",
        },
        "discounts": {
            "long_term_discount": "Available",
            "wellness_discount": "Available",
            "online_discount": "Available",
        },
        "optional_covers": {
            "buy_back_ped_waiting_period": "Available",
        },
    }


def write_product_intelligence(
    base_dir: Path,
    entity_id: str = ENTITY_ID,
    intelligence: dict | None = None,
) -> Path:
    insurer_slug, product_slug = entity_id.split(":")
    input_dir = (
        base_dir
        / "knowledge"
        / "health"
        / insurer_slug
        / product_slug
        / "intelligence"
    )
    input_dir.mkdir(parents=True)
    input_path = input_dir / "product_intelligence.json"
    input_path.write_text(
        json.dumps(intelligence or complete_product_intelligence()),
        encoding="utf-8",
    )
    return input_path


def write_validation_report(
    base_dir: Path,
    entity_id: str = ENTITY_ID,
    status: str = "PASS",
    score: int = 96,
    error_count: int = 0,
    warning_count: int = 2,
) -> Path:
    insurer_slug, product_slug = entity_id.split(":")
    validation_dir = (
        base_dir
        / "knowledge"
        / "health"
        / insurer_slug
        / product_slug
        / "validation"
    )
    validation_dir.mkdir(parents=True)
    validation_path = validation_dir / "product_intelligence_validation_report.json"
    validation_path.write_text(
        json.dumps(
            {
                "status": status,
                "score": score,
                "error_count": error_count,
                "warning_count": warning_count,
            }
        ),
        encoding="utf-8",
    )
    return validation_path


@pytest.fixture
def isolated_base_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_product_coverage, "BASE_DIR", tmp_path)
    return tmp_path


def product_with_sections(section_names: set[str]) -> dict:
    full_product = complete_product_intelligence()
    return {
        section: values
        for section, values in full_product.items()
        if section in section_names
    }


def assert_usable_with_review_score(score: float):
    assert 75 <= score < 90


def assert_partial_score(score: float):
    assert 50 <= score < 75


def test_audit_reports_ready_product_with_full_coverage(isolated_base_dir):
    write_product_intelligence(isolated_base_dir)

    report = audit_product_coverage.audit(ENTITY_ID)

    assert report["coverage_status"] == "READY"
    assert report["overall_coverage"] == 100.0
    assert report["missing_fields"] == []
    assert all(section["coverage"] == 100.0 for section in report["sections"].values())
    assert report["recommendations"] == [
        "Product coverage is strong enough for advisor-facing intelligence after review."
    ]
    assert report["output_file"] == (
        "knowledge/health/test_insurer/test_product/coverage/"
        "product_coverage_report.json"
    )

    output_path = isolated_base_dir / report["output_file"]
    assert json.loads(output_path.read_text(encoding="utf-8"))[
        "coverage_status"
    ] == "READY"


@pytest.mark.parametrize(
    ("sections", "expected_status", "score_assertion"),
    [
        (
            {
                "metadata",
                "eligibility",
                "sum_insured_options",
                "product_facts",
                "core_benefits",
                "discounts",
                "optional_covers",
            },
            "USABLE_WITH_REVIEW",
            assert_usable_with_review_score,
        ),
        (
            {
                "metadata",
                "eligibility",
                "sum_insured_options",
                "product_facts",
                "discounts",
            },
            "PARTIAL",
            assert_partial_score,
        ),
    ],
)
def test_audit_reports_reviewable_or_partial_products_with_missing_fields(
    isolated_base_dir,
    sections,
    expected_status,
    score_assertion,
):
    write_product_intelligence(
        isolated_base_dir,
        intelligence=product_with_sections(sections),
    )

    report = audit_product_coverage.audit(ENTITY_ID)

    assert report["coverage_status"] == expected_status
    score_assertion(report["overall_coverage"])
    assert report["missing_fields"]
    assert "Improve extraction coverage for missing fields." in report["recommendations"]


def test_audit_raises_when_product_intelligence_missing(isolated_base_dir):
    with pytest.raises(FileNotFoundError, match="Missing product intelligence file"):
        audit_product_coverage.audit(ENTITY_ID)


def test_audit_generates_recommendations_for_missing_fields(isolated_base_dir):
    intelligence = complete_product_intelligence()
    intelligence["metadata"]["uin"] = "XXXXX"
    intelligence["product_facts"]["room_rent_limit"] = ""
    write_product_intelligence(isolated_base_dir, intelligence=intelligence)

    report = audit_product_coverage.audit(ENTITY_ID)

    assert "metadata.uin" in report["missing_fields"]
    assert "product_facts.room_rent_limit" in report["missing_fields"]
    assert "Improve extraction coverage for missing fields." in report["recommendations"]


def test_audit_propagates_validation_quality_fields(isolated_base_dir):
    write_product_intelligence(isolated_base_dir)
    write_validation_report(
        isolated_base_dir,
        status="FAIL",
        score=67,
        error_count=1,
        warning_count=3,
    )

    report = audit_product_coverage.audit(ENTITY_ID)

    assert report["quality"] == {
        "validator_status": "FAIL",
        "validator_score": 67,
        "error_count": 1,
        "warning_count": 3,
    }
    assert "Fix validator errors before marking product as ready." in report[
        "recommendations"
    ]
    assert "Review warning-level quality issues for critical facts." in report[
        "recommendations"
    ]
