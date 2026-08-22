from __future__ import annotations

import json
from pathlib import Path

from insurance_intelligence.rule_certification.waiting_period import (
    build_waiting_period_certification_case,
    run_waiting_period_certification_case,
)


def _write_fixture(root: Path) -> Path:
    registration = {
        "document": {
            "document_id": "policy_wording_v1",
            "document_version_id": "docver_policy_wording_v1",
            "storage_locator": "fixtures/policy_wording.pdf",
            "content_sha256": "a" * 64,
            "document_type": "policy_wording",
        },
        "evidence_review": {
            "candidates": [
                {
                    "candidate_id": "candidate_page_21",
                    "excerpt": "Initial waiting period clause with accident and continuity exceptions and enhanced Sum Insured reapplication.",
                    "text_sha256": "abc123",
                    "source_page": 21,
                    "source_char_range": {"start": 100, "end": 200},
                },
                {
                    "candidate_id": "candidate_page_53",
                    "excerpt": "Initial Waiting period 30 days",
                    "text_sha256": "def456",
                    "source_page": 53,
                    "source_char_range": {"start": 500, "end": 600},
                },
            ]
        },
    }
    (root / "registration.json").write_text(json.dumps(registration), encoding="utf-8")
    bundle = {
        "registration_type": "generic_source_registration_bundle_v1",
        "product_context": {
            "insurer_id": "example_insurer",
            "product_id": "example_product",
            "product_display_name": "Example Product",
            "source_scope": "reusable_generic",
        },
        "sources": [
            {
                "document_id": "policy_wording_v1",
                "authority_role": "primary_legal",
                "registration_output_path": "registration.json",
            }
        ],
    }
    (root / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
    spec = {
        "schema_version": "1.0",
        "binding_type": "waiting_period_binding_v1",
        "binding_id": "example_initial_wait",
        "reviewed_by_human": True,
        "generic_source_bundle_path": "bundle.json",
        "evidence_selections": [
            {
                "role": "mechanism",
                "document_id": "policy_wording_v1",
                "candidate_id": "candidate_page_21",
                "candidate_text_sha256": "abc123",
            },
            {
                "role": "schedule_value_resolution",
                "document_id": "policy_wording_v1",
                "candidate_id": "candidate_page_53",
                "candidate_text_sha256": "def456",
            },
        ],
        "mechanic": {
            "waiting_period_type": "INITIAL",
            "duration_value": 30,
            "duration_unit": "DAYS",
            "start_basis": "POLICY_INCEPTION",
            "applies_to": ["illness_treatment_within_initial_wait"],
            "exclusions_or_exceptions": [
                "accident_claims_where_other_policy_terms_cover_the_claim",
                "insured_beneficiary_with_continuous_coverage_for_more_than_12_months",
            ],
            "modifications": [],
            "schedule_dependency": "Policy Schedule selects the duration; authoritative table resolves 30 days.",
            "continuity_dependency": "continuous coverage for more than 12 months removes this exclusion",
            "scope_type": "POLICY_WIDE",
            "scope_reference": None,
            "value_source": "POLICY_SCHEDULE_SELECTED",
            "member_waiting_basis": "POLICY_INCEPTION",
            "sum_insured_enhancement_effect": "REAPPLIES_TO_ENHANCED_PORTION",
        },
    }
    path = root / "spec.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


def test_generic_waiting_period_certification_passes_complete_resolved_mechanic(tmp_path: Path) -> None:
    spec_path = _write_fixture(tmp_path)

    case = build_waiting_period_certification_case(
        binding_spec_path="spec.json",
        repository_root=tmp_path,
    )
    result = run_waiting_period_certification_case(case)

    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert result.failures == ()
    assert {check.component_id for check in result.component_checks} == {
        "waiting_period_duration",
        "waiting_period_subject",
        "start_basis",
        "applicability_scope",
        "continuity_or_credit_rule",
        "exception_condition",
    }
    assert all(check.passed for check in result.component_checks)


def test_certification_preserves_schedule_resolution_and_enhanced_si_effect(tmp_path: Path) -> None:
    _write_fixture(tmp_path)

    case = build_waiting_period_certification_case(
        binding_spec_path="spec.json",
        repository_root=tmp_path,
    )
    packages = case.evidence_output.evidence_packages

    duration_packages = tuple(
        item for item in packages if item.field_or_topic == "WAITING_PERIOD_DURATION"
    )
    assert {item.page for item in duration_packages} == {21, 53}
    assert {item.retrieval_basis[1] for item in duration_packages} == {
        "mechanism",
        "schedule_value_resolution",
    }

    scope_package = next(
        item for item in packages if item.field_or_topic == "APPLICABILITY_SCOPE"
    )
    assert "REAPPLIES_TO_ENHANCED_PORTION" in scope_package.claim


def test_certification_keeps_binding_unpublished_and_scope_local(tmp_path: Path) -> None:
    _write_fixture(tmp_path)

    case = build_waiting_period_certification_case(
        binding_spec_path="spec.json",
        repository_root=tmp_path,
    )

    assert case.case_id == "waiting_period:example_initial_wait"
    assert any("bound_not_published" in item for item in case.evidence_output.limitations)
    assert any("does not certify other waiting-period families" in item for item in case.evidence_output.limitations)
