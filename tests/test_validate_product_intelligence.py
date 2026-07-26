import json
from collections import Counter
from pathlib import Path

import pytest

from scripts import validate_product_intelligence


ENTITY_ID = "test_insurer:test_product"


def validated_fact(value: str, *, candidate_values: list[str] | None = None) -> dict:
    fact = {
        "value": value,
        "source": "policy_wording.pdf",
        "confidence": 0.95,
        "validated": True,
        "validated_by": ["policy_wording.pdf", "brochure.pdf"],
    }
    if candidate_values is not None:
        fact["candidate_values"] = candidate_values
    return fact


def complete_product_intelligence() -> dict:
    return {
        "metadata": {
            "product_name": "Test Health Plan",
            "uin": "ABC1234567V01",
        },
        "waiting_periods": {
            "pre_existing_disease_waiting_period": validated_fact("36 months"),
            "specified_disease_waiting_period": validated_fact("24 months"),
            "initial_waiting_period": validated_fact("30 days"),
        },
        "product_facts": {
            "copay": validated_fact("No copay"),
            "room_rent_limit": validated_fact("Single private room"),
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


@pytest.fixture
def isolated_base_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(validate_product_intelligence, "BASE_DIR", tmp_path)
    return tmp_path


def issue_keys(report: dict) -> Counter:
    return Counter(
        (issue["severity"], issue["field"], issue["message"])
        for issue in report["issues"]
    )


def test_validate_passes_product_with_valid_metadata_and_critical_facts(
    isolated_base_dir,
):
    write_product_intelligence(isolated_base_dir)

    report = validate_product_intelligence.validate(ENTITY_ID)

    assert report["status"] == "PASS"
    assert report["score"] == 100
    assert report["issue_count"] == 0
    assert report["error_count"] == 0
    assert report["warning_count"] == 0
    assert report["issues"] == []


def test_validate_requires_review_when_critical_fact_lacks_cross_document_validation(
    isolated_base_dir,
):
    intelligence = complete_product_intelligence()
    intelligence["product_facts"]["copay"]["validated_by"] = []
    write_product_intelligence(isolated_base_dir, intelligence=intelligence)

    report = validate_product_intelligence.validate(ENTITY_ID)

    assert report["status"] == "REVIEW_REQUIRED"
    assert report["error_count"] == 0
    assert report["warning_count"] == 1
    assert report["issues"] == [
        {
            "severity": "WARN",
            "field": "product_facts.copay",
            "message": "Critical fact has no cross-document validation",
            "value": None,
        }
    ]


@pytest.mark.parametrize("uin", [None, "XXXXX12345"])
def test_validate_fails_when_uin_is_missing_or_placeholder(isolated_base_dir, uin):
    intelligence = complete_product_intelligence()
    intelligence["metadata"]["uin"] = uin
    write_product_intelligence(isolated_base_dir, intelligence=intelligence)

    report = validate_product_intelligence.validate(ENTITY_ID)

    assert report["status"] == "FAIL"
    assert report["error_count"] == 1
    assert report["warning_count"] == 0
    assert report["issues"] == [
        {
            "severity": "ERROR",
            "field": "metadata.uin",
            "message": "Invalid or placeholder UIN",
            "value": uin,
        }
    ]


def test_validate_prevents_duplicate_issues_for_required_facts(isolated_base_dir):
    intelligence = complete_product_intelligence()
    intelligence["waiting_periods"]["initial_waiting_period"] = {
        "value": "30 days",
        "confidence": 0.75,
        "validated": False,
        "validated_by": [],
    }
    write_product_intelligence(isolated_base_dir, intelligence=intelligence)

    report = validate_product_intelligence.validate(ENTITY_ID)

    keys = issue_keys(report)
    assert keys[
        (
            "ERROR",
            "waiting_periods.initial_waiting_period",
            "Missing primary source",
        )
    ] == 1
    assert keys[
        (
            "ERROR",
            "waiting_periods.initial_waiting_period",
            "Low confidence below 0.9",
        )
    ] == 1
    assert keys[
        (
            "ERROR",
            "waiting_periods.initial_waiting_period",
            "Fact is not validated",
        )
    ] == 1
    assert keys[
        (
            "WARN",
            "waiting_periods.initial_waiting_period",
            "Critical fact has no cross-document validation",
        )
    ] == 1


def test_validate_detects_conflicting_candidate_values(isolated_base_dir):
    intelligence = complete_product_intelligence()
    intelligence["waiting_periods"][
        "pre_existing_disease_waiting_period"
    ] = validated_fact(
        "36 months",
        candidate_values=["36 months", "48 months"],
    )
    write_product_intelligence(isolated_base_dir, intelligence=intelligence)

    report = validate_product_intelligence.validate(ENTITY_ID)

    conflict = next(
        issue
        for issue in report["issues"]
        if issue["message"] == "Conflicting candidate values detected"
    )
    assert report["status"] == "FAIL"
    assert conflict["severity"] == "ERROR"
    assert conflict["field"] == "waiting_periods.pre_existing_disease_waiting_period"
    assert set(conflict["value"]) == {"36 months", "48 months"}
