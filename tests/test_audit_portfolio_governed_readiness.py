import json
from pathlib import Path

import pytest

from scripts import audit_portfolio_coverage


@pytest.fixture
def isolated_base_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_portfolio_coverage, "BASE_DIR", tmp_path)
    (tmp_path / "knowledge" / "health").mkdir(parents=True)
    return tmp_path


def write_report(
    base_dir: Path,
    *,
    insurer: str,
    product: str,
    coverage: float = 100.0,
    coverage_status: str = "READY",
    governed_status: str | None = None,
):
    path = (
        base_dir
        / "knowledge"
        / "health"
        / insurer
        / product
        / "coverage"
        / "product_coverage_report.json"
    )
    path.parent.mkdir(parents=True)
    report = {
        "entity_id": f"{insurer}:{product}",
        "overall_coverage": coverage,
        "coverage_status": coverage_status,
        "sections": {"metadata": {"coverage": coverage}},
        "missing_fields": [],
        "quality": {
            "validator_status": "PASS",
            "validator_score": 100,
            "error_count": 0,
            "warning_count": 0,
        },
    }
    if governed_status is not None:
        report["governed_readiness"] = {"status": governed_status}
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_portfolio_does_not_treat_legacy_ready_as_governed_ready(isolated_base_dir):
    write_report(
        isolated_base_dir,
        insurer="test_insurer",
        product="test_product",
        coverage=100.0,
        coverage_status="READY",
    )

    report = audit_portfolio_coverage.audit_portfolio("health")

    summary = report["portfolio_summary"]
    assert summary["average_legacy_intelligence_coverage"] == 100.0
    assert summary["legacy_coverage_status_counts"] == {"READY": 1}
    assert summary["governed_readiness_status_counts"] == {"NOT_ASSESSED": 1}
    assert report["products"][0]["governed_readiness_status"] == "NOT_ASSESSED"
    assert report["products_requiring_attention"][0]["entity_id"] == "test_insurer:test_product"
    assert any("do not establish current or publication readiness" in item for item in report["recommendations"])


def test_portfolio_aggregates_governed_readiness_separately(isolated_base_dir):
    write_report(
        isolated_base_dir,
        insurer="a",
        product="one",
        coverage=100.0,
        coverage_status="READY",
        governed_status="READY",
    )
    write_report(
        isolated_base_dir,
        insurer="b",
        product="two",
        coverage=95.0,
        coverage_status="READY",
        governed_status="REVIEW_REQUIRED",
    )

    report = audit_portfolio_coverage.audit_portfolio("health")

    assert report["portfolio_summary"]["legacy_coverage_status_counts"] == {"READY": 2}
    assert report["portfolio_summary"]["governed_readiness_status_counts"] == {
        "READY": 1,
        "REVIEW_REQUIRED": 1,
    }
    attention_entities = {item["entity_id"] for item in report["products_requiring_attention"]}
    assert attention_entities == {"b:two"}


def test_portfolio_keeps_backward_compatible_coverage_summary_keys(isolated_base_dir):
    write_report(
        isolated_base_dir,
        insurer="test_insurer",
        product="test_product",
        coverage=80.0,
        coverage_status="USABLE_WITH_REVIEW",
        governed_status="NOT_ASSESSED",
    )

    report = audit_portfolio_coverage.audit_portfolio("health")
    summary = report["portfolio_summary"]

    assert summary["coverage_status_counts"] == {"USABLE_WITH_REVIEW": 1}
    assert summary["average_coverage"] == 80.0
    assert summary["average_legacy_intelligence_coverage"] == 80.0
