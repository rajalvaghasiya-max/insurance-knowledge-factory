from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory_core.governance.health_onboarding_batch_audit import (
    HealthOnboardingBatchAudit,
    HealthOnboardingBatchAuditError,
)


def _write_json(root: Path, relative: str, payload: dict) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _routing_payload() -> dict:
    return {
        "schema_version": "1.0",
        "routing_type": "governed_review_risk_routing_v1",
        "routing_status": "review_risk_routes_assigned_not_adjudicated",
        "routing_record_count": 2,
        "routing_records": [
            {"review_group_id": "g1"},
            {"review_group_id": "g2"},
        ],
        "workload_summary": {
            "tier_counts": {"critical": 1, "high": 0, "medium": 1, "low": 0},
            "route_counts": {},
        },
    }


def _spec() -> dict:
    return {
        "schema_version": "1.0",
        "audit_type": "phase_2a_health_onboarding_batch_audit_v1",
        "products": [
            {
                "entity_id": "insurer_a:product_a",
                "display_name": "Product A",
                "artifacts": {
                    "registration": "data/a_registration.json",
                    "review_risk_routing": "data/a_routing.json",
                },
            },
            {
                "entity_id": "insurer_b:product_b",
                "display_name": "Product B",
                "review_routing_applicability": "not_applicable_no_review_input",
                "artifacts": {
                    "registration": "data/b_registration.json"
                },
            },
        ],
    }


def test_batch_audit_is_spec_driven_and_reports_missing_artifacts(tmp_path: Path):
    _write_json(tmp_path, "data/a_registration.json", {"record": "a"})
    _write_json(tmp_path, "data/a_routing.json", _routing_payload())
    _write_json(tmp_path, "data/b_registration.json", {"record": "b"})

    result = HealthOnboardingBatchAudit.audit(spec=_spec(), repository_root=tmp_path).manifest

    assert result["product_count"] == 2
    assert result["batch_summary"]["review_routing_record_count"] == 2
    assert result["batch_summary"]["review_routing_not_applicable_no_review_input_count"] == 1
    assert result["batch_summary"]["review_risk_tier_counts"] == {
        "critical": 1,
        "high": 0,
        "medium": 1,
        "low": 0,
    }
    assert result["batch_summary"]["product_identity_bearing_production_code_changes"] == 0
    assert result["products"][0]["artifact_completeness_status"] == "incomplete_explicit"
    assert "classification" in result["products"][0]["missing_or_undeclared_artifacts"]
    assert result["products"][0]["product_specific_production_code_change_required"] is False
    assert result["products"][1]["artifacts"]["review_risk_routing"]["status"] == "not_applicable_no_review_input"
    assert "review_risk_routing" not in result["products"][1]["missing_or_undeclared_artifacts"]


def test_declared_missing_artifact_remains_explicit(tmp_path: Path):
    spec = _spec()
    spec["products"] = [{
        "entity_id": "insurer_a:product_a",
        "display_name": "Product A",
        "review_routing_applicability": "not_applicable_no_review_input",
        "artifacts": {"registration": "data/missing.json"},
    }]

    result = HealthOnboardingBatchAudit.audit(spec=spec, repository_root=tmp_path).manifest
    registration = result["products"][0]["artifacts"]["registration"]
    assert registration["status"] == "declared_missing"
    assert result["products"][0]["artifact_completeness_status"] == "incomplete_explicit"


def test_review_routing_not_applicable_does_not_create_fake_gap(tmp_path: Path):
    _write_json(tmp_path, "data/a_registration.json", {"record": "a"})
    spec = {
        "schema_version": "1.0",
        "audit_type": "phase_2a_health_onboarding_batch_audit_v1",
        "products": [{
            "entity_id": "insurer_a:product_a",
            "display_name": "Product A",
            "review_routing_applicability": "not_applicable_no_review_input",
            "artifacts": {
                "registration": "data/a_registration.json",
                "classification": "data/a_registration.json",
                "product_identity": "data/a_registration.json",
                "identity_resolution": "data/a_registration.json",
                "currentness_evidence": "data/a_registration.json",
            },
        }],
    }

    result = HealthOnboardingBatchAudit.audit(spec=spec, repository_root=tmp_path).manifest
    assert result["batch_summary"]["missing_or_undeclared_artifact_count"] == 0
    assert result["products"][0]["artifact_completeness_status"] == "complete_for_declared_audit"
    assert result["products"][0]["review_routing_applicability"] == "not_applicable_no_review_input"


def test_not_applicable_routing_rejects_declared_routing_artifact(tmp_path: Path):
    spec = _spec()
    spec["products"] = [spec["products"][1]]
    spec["products"][0]["artifacts"]["review_risk_routing"] = "data/routing.json"
    with pytest.raises(HealthOnboardingBatchAuditError, match="must not be declared"):
        HealthOnboardingBatchAudit.audit(spec=spec, repository_root=tmp_path)


def test_unknown_review_routing_applicability_fails_closed(tmp_path: Path):
    spec = _spec()
    spec["products"][0]["review_routing_applicability"] = "skip_review"
    with pytest.raises(HealthOnboardingBatchAuditError, match="unsupported review_routing_applicability"):
        HealthOnboardingBatchAudit.audit(spec=spec, repository_root=tmp_path)


def test_duplicate_product_identity_fails_closed(tmp_path: Path):
    spec = _spec()
    spec["products"][1]["entity_id"] = spec["products"][0]["entity_id"]
    with pytest.raises(HealthOnboardingBatchAuditError, match="unique"):
        HealthOnboardingBatchAudit.audit(spec=spec, repository_root=tmp_path)


def test_unknown_artifact_key_fails_closed(tmp_path: Path):
    spec = _spec()
    spec["products"][0]["artifacts"]["product_specific_python"] = "x.py"
    with pytest.raises(HealthOnboardingBatchAuditError, match="unsupported artifact key"):
        HealthOnboardingBatchAudit.audit(spec=spec, repository_root=tmp_path)


def test_invalid_routing_tier_counts_fail_closed(tmp_path: Path):
    _write_json(tmp_path, "data/a_registration.json", {"record": "a"})
    bad = _routing_payload()
    bad["workload_summary"]["tier_counts"]["critical"] = 2
    _write_json(tmp_path, "data/a_routing.json", bad)
    spec = _spec()
    spec["products"] = [spec["products"][0]]

    with pytest.raises(HealthOnboardingBatchAuditError, match="equal routing_record_count"):
        HealthOnboardingBatchAudit.audit(spec=spec, repository_root=tmp_path)


def test_path_traversal_is_rejected(tmp_path: Path):
    spec = _spec()
    spec["products"][0]["artifacts"]["registration"] = "../outside.json"
    with pytest.raises(HealthOnboardingBatchAuditError, match="safe repository-relative"):
        HealthOnboardingBatchAudit.audit(spec=spec, repository_root=tmp_path)
