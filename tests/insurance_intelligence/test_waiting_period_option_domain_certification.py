from __future__ import annotations

import json
from pathlib import Path

from insurance_intelligence.rule_certification.waiting_period_option_domain import (
    build_waiting_period_option_domain_certification_case,
    run_waiting_period_option_domain_certification_case,
)


def _write_governed_fixture(tmp_path: Path, *, specific_disease: bool) -> Path:
    source_path = tmp_path / "source.pdf"
    source_path.write_bytes(b"governed-source")
    registration = {
        "document": {
            "document_id": "example_document",
            "document_version_id": "example_document:v1",
            "storage_locator": "source.pdf",
            "content_sha256": "d" * 64,
            "document_type": "policy_wording",
        },
        "evidence_review": {
            "candidates": [
                {
                    "candidate_id": "candidate_page_20",
                    "source_page": 20,
                    "source_char_range": {"start": 10, "end": 20},
                    "text_sha256": "a" * 64,
                    "excerpt": "The waiting period as opted would be specified on the Policy Schedule.",
                },
                {
                    "candidate_id": "candidate_page_53",
                    "source_page": 53,
                    "source_char_range": {"start": 30, "end": 40},
                    "text_sha256": "b" * 64,
                    "excerpt": "Options available for change in waiting period: 1 year, 2 years, 3 years.",
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
    semantics = {
        "start_basis": "INSURED_PERSON_FIRST_COVERAGE",
        "continuity_credit": "reduced_to_extent_of_prior_coverage",
        "sum_insured_enhancement_effect": "REAPPLIES_TO_ENHANCED_PORTION",
    }
    if specific_disease:
        semantics.update(
            {
                "accident_exception": True,
                "longer_of_relationship": "the longer of PED and specified-disease waits applies",
            }
        )
    else:
        semantics["post_wait_condition"] = "PED must be declared and accepted"
    spec = {
        "schema_version": "1.0",
        "binding_type": "waiting_period_option_domain_binding_v1",
        "binding_id": "example_specific_options" if specific_disease else "example_ped_options",
        "reviewed_by_human": True,
        "generic_source_bundle_path": "bundle.json",
        "evidence_selections": [
            {
                "role": "mechanism",
                "document_id": "example_document",
                "candidate_id": "candidate_page_20",
                "candidate_text_sha256": "a" * 64,
            },
            {
                "role": "option_domain",
                "document_id": "example_document",
                "candidate_id": "candidate_page_53",
                "candidate_text_sha256": "b" * 64,
            },
        ],
        "option_domain": {
            "waiting_period_type": "SPECIFIC_DISEASE_PROCEDURE" if specific_disease else "PRE_EXISTING_DISEASE",
            "options": [
                {"duration_value": 1, "duration_unit": "YEARS"},
                {"duration_value": 2, "duration_unit": "YEARS"},
                {"duration_value": 3, "duration_unit": "YEARS"},
            ],
            "applies_to": ["listed_conditions"] if specific_disease else ["pre_existing_disease"],
            "schedule_dependency": "Selected in the Policy Schedule from 1, 2, or 3 years.",
            "scope_type": "POLICY_WIDE",
            "scope_reference": None,
            "value_source": "POLICY_SCHEDULE_SELECTED",
        },
        "material_mechanic_semantics": semantics,
    }
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    return spec_path


def _assert_common(case, result) -> None:
    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert result.failures == ()
    checks = {item.component_id: item for item in result.component_checks}
    for required in (
        "duration_option_domain",
        "waiting_period_subject",
        "selection_basis",
        "start_basis",
        "applicability_scope",
        "continuity_or_credit_rule",
        "sum_insured_enhancement_effect",
    ):
        assert checks[required].passed is True
    duration_packages = [
        item for item in case.evidence_output.evidence_packages
        if item.field_or_topic == "WAITING_PERIOD_DURATION_OPTION_DOMAIN"
    ]
    assert len(duration_packages) == 1
    assert duration_packages[0].page == 53
    assert "1 YEARS; 2 YEARS; 3 YEARS" in duration_packages[0].claim
    assert "No duration is selected" in duration_packages[0].claim
    selection_packages = [
        item for item in case.evidence_output.evidence_packages
        if item.field_or_topic == "WAITING_PERIOD_SELECTION_BASIS"
    ]
    assert {item.page for item in selection_packages} == {20, 53}


def test_certifies_ped_unresolved_option_domain_and_material_mechanics(tmp_path: Path) -> None:
    spec_path = _write_governed_fixture(tmp_path, specific_disease=False)
    case = build_waiting_period_option_domain_certification_case(
        binding_spec_path=spec_path.name,
        repository_root=tmp_path,
    )
    result = run_waiting_period_option_domain_certification_case(case)
    _assert_common(case, result)
    checks = {item.component_id: item for item in result.component_checks}
    assert checks["post_wait_condition"].passed is True
    assert "exception_condition" not in checks
    assert "relationship_rule" not in checks


def test_certifies_specific_disease_domain_with_exception_and_relationship(tmp_path: Path) -> None:
    spec_path = _write_governed_fixture(tmp_path, specific_disease=True)
    case = build_waiting_period_option_domain_certification_case(
        binding_spec_path=spec_path.name,
        repository_root=tmp_path,
    )
    result = run_waiting_period_option_domain_certification_case(case)
    _assert_common(case, result)
    checks = {item.component_id: item for item in result.component_checks}
    assert checks["exception_condition"].passed is True
    assert checks["relationship_rule"].passed is True
    assert "post_wait_condition" not in checks
