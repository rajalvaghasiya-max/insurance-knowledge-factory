from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory_core.canonical.waiting_period_option_domain_multispan_binding import (
    WaitingPeriodOptionDomainMultispanBinding,
    WaitingPeriodOptionDomainMultispanBindingError,
)


def _fixture(tmp_path: Path) -> dict:
    (tmp_path / "registration.json").write_text(
        json.dumps(
            {
                "evidence_review": {
                    "candidates": [
                        {
                            "candidate_id": "candidate_page_30",
                            "source_page": 30,
                            "source_char_range": {"start": 10, "end": 20},
                            "text_sha256": "a" * 64,
                        },
                        {
                            "candidate_id": "candidate_page_31",
                            "source_page": 31,
                            "source_char_range": {"start": 21, "end": 30},
                            "text_sha256": "b" * 64,
                        },
                        {
                            "candidate_id": "candidate_page_26",
                            "source_page": 26,
                            "source_char_range": {"start": 31, "end": 40},
                            "text_sha256": "c" * 64,
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "bundle.json").write_text(
        json.dumps(
            {
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
        ),
        encoding="utf-8",
    )
    return {
        "schema_version": "1.0",
        "binding_type": "waiting_period_option_domain_multispan_binding_v1",
        "binding_id": "example_ped_options_full_mechanics",
        "reviewed_by_human": True,
        "generic_source_bundle_path": "bundle.json",
        "evidence_selections": [
            {
                "role": "mechanism",
                "document_id": "example_document",
                "candidate_id": "candidate_page_30",
                "candidate_text_sha256": "a" * 64,
            },
            {
                "role": "mechanism",
                "document_id": "example_document",
                "candidate_id": "candidate_page_31",
                "candidate_text_sha256": "b" * 64,
            },
            {
                "role": "option_domain",
                "document_id": "example_document",
                "candidate_id": "candidate_page_26",
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
            "applies_to": ["pre_existing_disease_and_direct_complications"],
            "schedule_dependency": "Selected in the Policy Schedule.",
            "scope_type": "POLICY_WIDE",
            "scope_reference": None,
            "value_source": "POLICY_SCHEDULE_SELECTED",
        },
    }


def test_binds_multiple_mechanism_candidates_without_selecting_scalar(tmp_path: Path) -> None:
    result = WaitingPeriodOptionDomainMultispanBinding().bind(
        spec=_fixture(tmp_path),
        repository_root=tmp_path,
        bound_at="2026-08-22T00:00:00+00:00",
    )
    manifest = result.manifest

    assert manifest["binding_type"] == "waiting_period_option_domain_multispan_binding_v1"
    assert manifest["binding_status"] == "reviewed_waiting_period_option_domain_bound_not_published"
    assert manifest["resolution_status"] == "unresolved_schedule_option_domain"
    assert manifest["policy_instance_resolution_status"] == "not_resolved_without_schedule_selection"
    assert manifest["mechanism_evidence_span_count"] == 2
    assert [item["role"] for item in manifest["evidence"]] == [
        "mechanism",
        "mechanism",
        "option_domain",
    ]
    assert [item["source_page"] for item in manifest["evidence"]] == [30, 31, 26]
    assert len(manifest["option_domain"]["evidence_reference_ids"]) == 3
    assert "selected_duration" not in manifest["option_domain"]


def test_requires_at_least_one_mechanism_and_exactly_one_option_domain(tmp_path: Path) -> None:
    spec = _fixture(tmp_path)
    spec["evidence_selections"] = spec["evidence_selections"][:2]

    with pytest.raises(
        WaitingPeriodOptionDomainMultispanBindingError,
        match="one or more mechanism selections and exactly one option_domain",
    ):
        WaitingPeriodOptionDomainMultispanBinding().bind(
            spec=spec,
            repository_root=tmp_path,
        )


def test_rejects_duplicate_candidate_selection(tmp_path: Path) -> None:
    spec = _fixture(tmp_path)
    spec["evidence_selections"].insert(1, dict(spec["evidence_selections"][0]))

    with pytest.raises(
        WaitingPeriodOptionDomainMultispanBindingError,
        match="duplicate evidence selections",
    ):
        WaitingPeriodOptionDomainMultispanBinding().bind(
            spec=spec,
            repository_root=tmp_path,
        )


def test_fails_closed_when_any_additional_mechanism_hash_mismatches(tmp_path: Path) -> None:
    spec = _fixture(tmp_path)
    spec["evidence_selections"][1]["candidate_text_sha256"] = "d" * 64

    with pytest.raises(
        WaitingPeriodOptionDomainMultispanBindingError,
        match="candidate text hash mismatch",
    ):
        WaitingPeriodOptionDomainMultispanBinding().bind(
            spec=spec,
            repository_root=tmp_path,
        )
