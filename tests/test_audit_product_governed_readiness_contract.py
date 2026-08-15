from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory_core.governance.governed_readiness import GovernedReadinessContractError
from scripts import audit_product_coverage


ENTITY_ID = "test_insurer:test_product"


def _complete_product_intelligence() -> dict:
    return {
        "metadata": {"product_name": "Test Plan", "uin": "TEST123V01"},
        "eligibility": {"adult_entry_age": "18 years", "dependent_child_entry_age": "91 days"},
        "sum_insured_options": {"values": ["500000"]},
        "waiting_periods": {
            "pre_existing_disease_waiting_period": "36 months",
            "specified_disease_waiting_period": "24 months",
            "initial_waiting_period": "30 days",
            "delivery_newborn_waiting_period": "24 months",
            "bariatric_surgery_waiting_period": "24 months",
        },
        "product_facts": {"copay": "No copay", "room_rent_limit": "Single private room"},
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
        "optional_covers": {"buy_back_ped_waiting_period": "Available"},
    }


def _write_product(base_dir: Path) -> None:
    path = base_dir / "knowledge/health/test_insurer/test_product/intelligence/product_intelligence.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_complete_product_intelligence()), encoding="utf-8")


def _write_readiness(base_dir: Path, data: dict) -> None:
    path = base_dir / "knowledge/health/test_insurer/test_product/governance/governed_readiness.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def isolated_base_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_product_coverage, "BASE_DIR", tmp_path)
    _write_product(tmp_path)
    return tmp_path


def test_audit_derives_ready_for_publication_review_from_assessed_dimensions(isolated_base_dir):
    _write_readiness(
        isolated_base_dir,
        {
            "assessment_version": "0.1",
            "entity_id": ENTITY_ID,
            "source_governance": "CURRENT_GOVERNED",
            "semantic_review": "COMPLETE",
            "applicability": "RESOLVED",
            "publication_eligibility": "ELIGIBLE",
            "publication_state": "NOT_PUBLISHED",
            "unresolved_residue": [],
            "evidence_references": ["governance/source.json", "governance/review.json"],
            "note": "Reviewed governed assessment.",
        },
    )

    report = audit_product_coverage.audit(ENTITY_ID)

    assert report["coverage_status"] == "READY"
    assert report["governed_readiness"]["status"] == "READY_FOR_PUBLICATION_REVIEW"
    assert report["governed_readiness"]["publication_state"] == "NOT_PUBLISHED"
    assert report["governed_readiness"]["evidence_references"] == [
        "governance/source.json",
        "governance/review.json",
    ]


def test_audit_rejects_asserted_summary_status(isolated_base_dir):
    _write_readiness(
        isolated_base_dir,
        {
            "entity_id": ENTITY_ID,
            "source_governance": "CURRENT_GOVERNED",
            "semantic_review": "COMPLETE",
            "applicability": "RESOLVED",
            "publication_eligibility": "ELIGIBLE",
            "publication_state": "NOT_PUBLISHED",
            "unresolved_residue": [],
            "evidence_references": ["governance/review.json"],
            "status": "PUBLISHED",
        },
    )

    with pytest.raises(
        GovernedReadinessContractError,
        match="unknown governed-readiness field.*status",
    ):
        audit_product_coverage.audit(ENTITY_ID)


def test_audit_preserves_residue_as_review_required(isolated_base_dir):
    _write_readiness(
        isolated_base_dir,
        {
            "entity_id": ENTITY_ID,
            "source_governance": "CURRENT_GOVERNED",
            "semantic_review": "COMPLETE",
            "applicability": "RESOLVED",
            "publication_eligibility": "ELIGIBLE",
            "publication_state": "NOT_PUBLISHED",
            "unresolved_residue": ["Policy schedule binding remains unresolved"],
            "evidence_references": ["governance/review.json"],
        },
    )

    report = audit_product_coverage.audit(ENTITY_ID)

    assert report["governed_readiness"]["status"] == "REVIEW_REQUIRED"
    assert report["governed_readiness"]["unresolved_residue"] == [
        "Policy schedule binding remains unresolved"
    ]
