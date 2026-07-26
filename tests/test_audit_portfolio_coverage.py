import json
from pathlib import Path

import pytest

from scripts import audit_portfolio_coverage


DOMAIN = "health"


def write_coverage_report(
    base_dir: Path,
    insurer_slug: str,
    product_slug: str,
    *,
    entity_id: str | None = None,
    overall_coverage: float = 100.0,
    coverage_status: str = "READY",
    validator_status: str = "PASS",
    validator_score: float | None = 95.0,
    error_count: int = 0,
    warning_count: int = 0,
    missing_fields: list[str] | None = None,
    sections: dict | None = None,
) -> Path:
    report_dir = (
        base_dir
        / "knowledge"
        / DOMAIN
        / insurer_slug
        / product_slug
        / "coverage"
    )
    report_dir.mkdir(parents=True)
    report_path = report_dir / "product_coverage_report.json"
    report = {
        "entity_id": entity_id or f"{insurer_slug}:{product_slug}",
        "overall_coverage": overall_coverage,
        "coverage_status": coverage_status,
        "sections": sections
        or {
            "metadata": {"coverage": overall_coverage},
            "core_benefits": {"coverage": overall_coverage},
        },
        "missing_fields": missing_fields or [],
        "quality": {
            "validator_status": validator_status,
            "validator_score": validator_score,
            "error_count": error_count,
            "warning_count": warning_count,
        },
    }
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return report_path


@pytest.fixture
def isolated_base_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_portfolio_coverage, "BASE_DIR", tmp_path)
    return tmp_path


def test_audit_portfolio_summarizes_multiple_products(isolated_base_dir):
    write_coverage_report(
        isolated_base_dir,
        "insurer_a",
        "product_a",
        overall_coverage=95.0,
        coverage_status="READY",
        validator_status="PASS",
    )
    write_coverage_report(
        isolated_base_dir,
        "insurer_b",
        "product_b",
        overall_coverage=82.0,
        coverage_status="USABLE_WITH_REVIEW",
        validator_status="REVIEW_REQUIRED",
    )

    report = audit_portfolio_coverage.audit_portfolio(DOMAIN)

    assert report["domain"] == DOMAIN
    assert report["portfolio_summary"]["total_products"] == 2
    assert report["portfolio_summary"]["coverage_status_counts"] == {
        "READY": 1,
        "USABLE_WITH_REVIEW": 1,
    }
    assert report["portfolio_summary"]["validator_status_counts"] == {
        "PASS": 1,
        "REVIEW_REQUIRED": 1,
    }
    assert [product["entity_id"] for product in report["products"]] == [
        "insurer_a:product_a",
        "insurer_b:product_b",
    ]
    assert report["output_file"] == (
        "knowledge/health/portfolio/portfolio_coverage_report.json"
    )

    output_path = isolated_base_dir / report["output_file"]
    assert json.loads(output_path.read_text(encoding="utf-8"))[
        "portfolio_summary"
    ]["total_products"] == 2


def test_audit_portfolio_calculates_average_coverage(isolated_base_dir):
    write_coverage_report(
        isolated_base_dir,
        "insurer_a",
        "product_a",
        overall_coverage=91.25,
    )
    write_coverage_report(
        isolated_base_dir,
        "insurer_b",
        "product_b",
        overall_coverage=76.25,
    )
    write_coverage_report(
        isolated_base_dir,
        "insurer_c",
        "product_c",
        overall_coverage=82.5,
    )

    report = audit_portfolio_coverage.audit_portfolio(DOMAIN)

    assert report["portfolio_summary"]["average_coverage"] == 83.33


def test_audit_portfolio_aggregates_top_missing_fields(isolated_base_dir):
    write_coverage_report(
        isolated_base_dir,
        "insurer_a",
        "product_a",
        missing_fields=[
            "metadata.uin",
            "product_facts.room_rent_limit",
        ],
    )
    write_coverage_report(
        isolated_base_dir,
        "insurer_b",
        "product_b",
        missing_fields=[
            "metadata.uin",
            "waiting_periods.initial_waiting_period",
        ],
    )
    write_coverage_report(
        isolated_base_dir,
        "insurer_c",
        "product_c",
        missing_fields=["metadata.uin"],
    )

    report = audit_portfolio_coverage.audit_portfolio(DOMAIN)

    assert report["top_missing_fields"][0] == {
        "field": "metadata.uin",
        "missing_in_products": 3,
    }
    assert {
        item["field"]: item["missing_in_products"]
        for item in report["top_missing_fields"]
    } == {
        "metadata.uin": 3,
        "product_facts.room_rent_limit": 1,
        "waiting_periods.initial_waiting_period": 1,
    }
    assert (
        "Prioritize extractor improvement for 'metadata.uin', missing in 3 product(s)."
        in report["recommendations"]
    )


def test_audit_portfolio_lists_products_requiring_attention(isolated_base_dir):
    write_coverage_report(
        isolated_base_dir,
        "insurer_ready",
        "product_ready",
        overall_coverage=94.0,
        coverage_status="READY",
        validator_status="PASS",
    )
    write_coverage_report(
        isolated_base_dir,
        "insurer_low",
        "product_low",
        overall_coverage=84.0,
        coverage_status="USABLE_WITH_REVIEW",
        validator_status="PASS",
    )
    write_coverage_report(
        isolated_base_dir,
        "insurer_partial",
        "product_partial",
        overall_coverage=70.0,
        coverage_status="PARTIAL",
        validator_status="PASS",
    )
    write_coverage_report(
        isolated_base_dir,
        "insurer_quality",
        "product_quality",
        overall_coverage=96.0,
        coverage_status="READY",
        validator_status="FAIL",
        error_count=1,
    )

    report = audit_portfolio_coverage.audit_portfolio(DOMAIN)

    assert [
        product["entity_id"] for product in report["products_requiring_attention"]
    ] == [
        "insurer_quality:product_quality",
        "insurer_partial:product_partial",
        "insurer_low:product_low",
    ]
    assert (
        "Review products requiring attention before using them in advisor-facing workflows."
        in report["recommendations"]
    )


def test_audit_portfolio_handles_empty_portfolio(isolated_base_dir):
    (isolated_base_dir / "knowledge" / DOMAIN).mkdir(parents=True)

    report = audit_portfolio_coverage.audit_portfolio(DOMAIN)

    assert report["portfolio_summary"] == {
        "total_products": 0,
        "coverage_status_counts": {},
        "validator_status_counts": {},
        "average_coverage": 0,
        "average_validator_score": None,
    }
    assert report["section_coverage_summary"] == {}
    assert report["top_missing_fields"] == []
    assert report["products_requiring_attention"] == []
    assert report["products"] == []
    assert report["recommendations"] == [
        "No product coverage reports found. Run product-level coverage audits first."
    ]
