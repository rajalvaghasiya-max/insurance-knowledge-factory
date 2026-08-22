from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory_core.canonical.waiting_period_option_domain_binding import (
    WaitingPeriodOptionDomainBinding,
    WaitingPeriodOptionDomainBindingError,
)


def _fixture(tmp_path: Path) -> dict:
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        json.dumps({
            "evidence_review": {
                "candidates": [
                    {
                        "candidate_id": "candidate_page_20",
                        "source_page": 20,
                        "source_char_range": {"start": 10, "end": 20},
                        "text_sha256": "a" * 64,
                    },
                    {
                        "candidate_id": "candidate_page_53",
                        "source_page": 53,
                        "source_char_range": {"start": 30, "end": 40},
                        "text_sha256": "b" * 64,
                    },
                ]
            }
        }),
        encoding="utf-8",
    )
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(
        json.dumps({
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
        }),
        encoding="utf-8",
    )
    return {
        "schema_version": "1.0",
        "binding_type": "waiting_period_option_domain_binding_v1",
        "binding_id": "example_ped_options",
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
            "waiting_period_type": "PRE_EXISTING_DISEASE",
            "options": [
                {"duration_value": 1, "duration_unit": "YEARS"},
                {"duration_value": 2, "duration_unit": "YEARS"},
                {"duration_value": 3, "duration_unit": "YEARS"},
            ],
            "applies_to": ["pre_existing_disease"],
            "schedule_dependency": "Selected in the Policy Schedule.",
            "scope_type": "POLICY_WIDE",
            "scope_reference": None,
            "value_source": "POLICY_SCHEDULE_SELECTED",
        },
    }


def test_binds_unresolved_schedule_option_domain_without_selecting_scalar(tmp_path: Path) -> None:
    spec = _fixture(tmp_path)
    result = WaitingPeriodOptionDomainBinding().bind(
        spec=spec,
        repository_root=tmp_path,
        bound_at="2026-08-22T00:00:00+00:00",
    )
    manifest = result.manifest
    assert manifest["binding_status"] == "reviewed_waiting_period_option_domain_bound_not_published"
    assert manifest["resolution_status"] == "unresolved_schedule_option_domain"
    assert manifest["policy_instance_resolution_status"] == "not_resolved_without_schedule_selection"
    assert manifest["publication_status"] == "bound_not_published"
    assert manifest["option_domain"]["options"] == [
        {"duration_value": 1, "duration_unit": "YEARS"},
        {"duration_value": 2, "duration_unit": "YEARS"},
        {"duration_value": 3, "duration_unit": "YEARS"},
    ]
    assert "selected_duration" not in manifest["option_domain"]
    assert [item["role"] for item in manifest["evidence"]] == ["mechanism", "option_domain"]


def test_requires_both_mechanism_and_option_domain_evidence(tmp_path: Path) -> None:
    spec = _fixture(tmp_path)
    spec["evidence_selections"] = spec["evidence_selections"][:1]
    with pytest.raises(WaitingPeriodOptionDomainBindingError, match="exactly one mechanism and one option_domain"):
        WaitingPeriodOptionDomainBinding().bind(spec=spec, repository_root=tmp_path)


def test_fails_closed_on_candidate_hash_mismatch(tmp_path: Path) -> None:
    spec = _fixture(tmp_path)
    spec["evidence_selections"][1]["candidate_text_sha256"] = "c" * 64
    with pytest.raises(WaitingPeriodOptionDomainBindingError, match="candidate text hash mismatch"):
        WaitingPeriodOptionDomainBinding().bind(spec=spec, repository_root=tmp_path)
