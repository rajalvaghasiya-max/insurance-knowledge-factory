from __future__ import annotations

import json
from pathlib import Path

import pytest

from insurance_intelligence.rule_certification.waiting_period_modification import (
    WaitingPeriodModificationCertificationError,
    build_waiting_period_modification_certification_case,
    run_waiting_period_modification_certification_case,
)


def _write_fixture(tmp_path: Path, *, include_modification: bool = True) -> str:
    source_path = tmp_path / "source.txt"
    source_path.write_text("governed waiting-period source", encoding="utf-8")

    registration = {
        "document": {
            "document_id": "example_document",
            "document_version_id": "example_document:v1",
            "storage_locator": "source.txt",
            "content_sha256": "a" * 64,
            "document_type": "policy_wording",
        },
        "evidence_review": {
            "candidates": [
                {
                    "candidate_id": "candidate_page_21",
                    "source_page": 21,
                    "excerpt": "Maternity waiting period is as specified in the Policy Schedule.",
                    "source_char_range": {"start": 10, "end": 80},
                    "text_sha256": "b" * 64,
                },
                {
                    "candidate_id": "candidate_page_53",
                    "source_page": 53,
                    "excerpt": "Maternity waiting period 36 months; decreases by 1 year if long-term premium is paid upfront.",
                    "source_char_range": {"start": 90, "end": 190},
                    "text_sha256": "c" * 64,
                },
            ]
        },
    }
    (tmp_path / "registration.json").write_text(json.dumps(registration), encoding="utf-8")

    bundle = {
        "registration_type": "generic_source_registration_bundle_v1",
        "product_context": {
            "source_scope": "reusable_generic",
            "insurer_id": "example_insurer",
            "product_id": "example_product",
            "product_display_name": "Example Product",
        },
        "sources": [
            {
                "document_id": "example_document",
                "authority_role": "primary_legal",
                "registration_output_path": "registration.json",
            }
        ],
    }
    (tmp_path / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")

    modifications = []
    if include_modification:
        modifications = [
            {
                "modification_type": "REDUCTION",
                "condition": "premium_for_long_term_policy_is_paid_upfront",
                "resulting_duration_value": 24,
                "resulting_duration_unit": "MONTHS",
                "evidence_reference_ids": [],
            }
        ]

    spec = {
        "schema_version": "1.0",
        "binding_type": "waiting_period_binding_v1",
        "binding_id": "example_maternity_wait_36_months",
        "reviewed_by_human": True,
        "generic_source_bundle_path": "bundle.json",
        "evidence_selections": [
            {
                "role": "mechanism",
                "document_id": "example_document",
                "candidate_id": "candidate_page_21",
                "candidate_text_sha256": "b" * 64,
            },
            {
                "role": "schedule_value_resolution",
                "document_id": "example_document",
                "candidate_id": "candidate_page_53",
                "candidate_text_sha256": "c" * 64,
            },
        ],
        "mechanic": {
            "waiting_period_type": "MATERNITY",
            "duration_value": 36,
            "duration_unit": "MONTHS",
            "start_basis": "INSURED_PERSON_FIRST_COVERAGE",
            "applies_to": ["maternity_package_expenses"],
            "exclusions_or_exceptions": ["ectopic_pregnancy_exception"],
            "modifications": modifications,
            "schedule_dependency": "Selected in the Policy Schedule.",
            "continuity_dependency": None,
            "scope_type": "BENEFIT_SCOPED",
            "scope_reference": "maternity_package_expenses",
            "value_source": "POLICY_SCHEDULE_SELECTED",
            "member_waiting_basis": "POLICY_INCEPTION",
            "sum_insured_enhancement_effect": None,
        },
    }
    path = tmp_path / "binding.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return "binding.json"


def test_certifies_schedule_evidenced_duration_reduction(tmp_path: Path) -> None:
    spec_path = _write_fixture(tmp_path)
    case = build_waiting_period_modification_certification_case(
        binding_spec_path=spec_path,
        repository_root=tmp_path,
    )
    result = run_waiting_period_modification_certification_case(case)

    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    modification_check = next(
        item for item in result.component_checks if item.component_id == "modification_rule"
    )
    assert modification_check.actual_status == "SATISFIED"
    assert modification_check.passed is True

    packages = [
        item
        for item in case.evidence_output.evidence_packages
        if item.field_or_topic == "WAITING_PERIOD_MODIFICATION_RULE"
    ]
    assert len(packages) == 1
    package = packages[0]
    assert package.page == 53
    assert package.retrieval_basis[1] == "schedule_value_resolution"
    assert "REDUCTION" in package.claim
    assert "24 MONTHS" in package.claim
    assert "premium_for_long_term_policy_is_paid_upfront" in package.claim


def test_rejects_modification_certification_when_spec_has_no_modification(tmp_path: Path) -> None:
    spec_path = _write_fixture(tmp_path, include_modification=False)
    with pytest.raises(
        WaitingPeriodModificationCertificationError,
        match="does not contain waiting-period modifications",
    ):
        build_waiting_period_modification_certification_case(
            binding_spec_path=spec_path,
            repository_root=tmp_path,
        )
