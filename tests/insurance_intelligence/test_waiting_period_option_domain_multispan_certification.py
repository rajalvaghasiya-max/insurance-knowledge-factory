from __future__ import annotations

import json
from pathlib import Path

import pytest

from insurance_intelligence.rule_certification.waiting_period_option_domain_multispan import (
    WaitingPeriodOptionDomainMultispanCertificationError,
    build_waiting_period_option_domain_multispan_certification_case,
    run_waiting_period_option_domain_multispan_certification_case,
)


def _fixture(tmp_path: Path) -> Path:
    (tmp_path / "source.pdf").write_bytes(b"source")
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
                    "candidate_id": "candidate_page_10",
                    "source_page": 10,
                    "source_char_range": {"start": 0, "end": 10},
                    "text_sha256": "a" * 64,
                    "excerpt": "PED wait is selected in the Policy Schedule from first coverage.",
                },
                {
                    "candidate_id": "candidate_page_11",
                    "source_page": 11,
                    "source_char_range": {"start": 11, "end": 20},
                    "text_sha256": "b" * 64,
                    "excerpt": "Continuity credit applies; enhanced SI reapplies; PED must be declared and accepted.",
                },
                {
                    "candidate_id": "candidate_page_20",
                    "source_page": 20,
                    "source_char_range": {"start": 21, "end": 30},
                    "text_sha256": "c" * 64,
                    "excerpt": "PED waiting period options are 12, 24, or 36 months.",
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
    spec = {
        "schema_version": "1.0",
        "binding_type": "waiting_period_option_domain_multispan_binding_v1",
        "binding_id": "example_ped_full",
        "reviewed_by_human": True,
        "generic_source_bundle_path": "bundle.json",
        "evidence_selections": [
            {
                "role": "mechanism",
                "document_id": "example_document",
                "candidate_id": "candidate_page_10",
                "candidate_text_sha256": "a" * 64,
            },
            {
                "role": "mechanism",
                "document_id": "example_document",
                "candidate_id": "candidate_page_11",
                "candidate_text_sha256": "b" * 64,
            },
            {
                "role": "option_domain",
                "document_id": "example_document",
                "candidate_id": "candidate_page_20",
                "candidate_text_sha256": "c" * 64,
            },
        ],
        "option_domain": {
            "waiting_period_type": "PRE_EXISTING_DISEASE",
            "options": [
                {"duration_value": 12, "duration_unit": "MONTHS"},
                {"duration_value": 24, "duration_unit": "MONTHS"},
                {"duration_value": 36, "duration_unit": "MONTHS"},
            ],
            "applies_to": ["pre_existing_disease"],
            "schedule_dependency": "Selected in the Policy Schedule.",
            "scope_type": "POLICY_WIDE",
            "scope_reference": None,
            "value_source": "POLICY_SCHEDULE_SELECTED",
        },
        "material_mechanic_semantics": {
            "start_basis": "INSURED_PERSON_FIRST_COVERAGE",
            "continuity_credit": "reduced_to_extent_of_prior_coverage",
            "sum_insured_enhancement_effect": "REAPPLIES_TO_ENHANCED_PORTION",
            "post_wait_condition": "PED must be declared and accepted",
        },
        "component_evidence_candidate_ids": {
            "duration_option_domain": ["candidate_page_20"],
            "waiting_period_subject": ["candidate_page_10"],
            "selection_basis": ["candidate_page_10", "candidate_page_20"],
            "start_basis": ["candidate_page_10"],
            "applicability_scope": ["candidate_page_10"],
            "continuity_or_credit_rule": ["candidate_page_11"],
            "sum_insured_enhancement_effect": ["candidate_page_11"],
            "post_wait_condition": ["candidate_page_11"],
        },
    }
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


def test_certifies_multispan_ped_with_component_specific_evidence(tmp_path: Path) -> None:
    spec_path = _fixture(tmp_path)
    case = build_waiting_period_option_domain_multispan_certification_case(
        binding_spec_path=spec_path.name,
        repository_root=tmp_path,
    )
    result = run_waiting_period_option_domain_multispan_certification_case(case)

    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert result.failures == ()
    checks = {item.component_id: item for item in result.component_checks}
    for component_id in (
        "duration_option_domain",
        "waiting_period_subject",
        "selection_basis",
        "start_basis",
        "applicability_scope",
        "continuity_or_credit_rule",
        "sum_insured_enhancement_effect",
        "post_wait_condition",
    ):
        assert checks[component_id].passed is True

    packages = case.evidence_output.evidence_packages
    by_topic = {}
    for package in packages:
        by_topic.setdefault(package.field_or_topic, []).append(package)

    assert {item.page for item in by_topic["WAITING_PERIOD_SELECTION_BASIS"]} == {10, 20}
    assert {item.page for item in by_topic["CONTINUITY_OR_CREDIT_RULE"]} == {11}
    assert {item.page for item in by_topic["SUM_INSURED_ENHANCEMENT_EFFECT"]} == {11}
    assert {item.page for item in by_topic["POST_WAIT_CONDITION"]} == {11}
    assert {item.page for item in by_topic["WAITING_PERIOD_DURATION_OPTION_DOMAIN"]} == {20}
    assert all(
        item.retrieval_basis[0] == "reviewed_waiting_period_option_domain_multispan_binding"
        for item in packages
    )


def test_fails_closed_when_component_map_references_unbound_candidate(tmp_path: Path) -> None:
    spec_path = _fixture(tmp_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["component_evidence_candidate_ids"]["post_wait_condition"] = ["candidate_page_99"]
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    with pytest.raises(
        WaitingPeriodOptionDomainMultispanCertificationError,
        match="references unbound candidate",
    ):
        build_waiting_period_option_domain_multispan_certification_case(
            binding_spec_path=spec_path.name,
            repository_root=tmp_path,
        )


def test_fails_closed_when_component_map_omits_material_semantic(tmp_path: Path) -> None:
    spec_path = _fixture(tmp_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    del spec["component_evidence_candidate_ids"]["continuity_or_credit_rule"]
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    with pytest.raises(
        WaitingPeriodOptionDomainMultispanCertificationError,
        match="must exactly cover certified components",
    ):
        build_waiting_period_option_domain_multispan_certification_case(
            binding_spec_path=spec_path.name,
            repository_root=tmp_path,
        )
