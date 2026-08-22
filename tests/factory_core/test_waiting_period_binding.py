from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory_core.canonical.waiting_period_binding import (
    WaitingPeriodBinding,
    WaitingPeriodBindingError,
)


def _write_fixture(root: Path) -> dict:
    registration = {
        "evidence_review": {
            "candidates": [
                {
                    "candidate_id": "candidate_page_21",
                    "text_sha256": "abc123",
                    "source_page": 21,
                    "source_char_range": {"start": 100, "end": 200},
                },
                {
                    "candidate_id": "candidate_page_53",
                    "text_sha256": "def456",
                    "source_page": 53,
                    "source_char_range": {"start": 500, "end": 600},
                },
            ]
        }
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
    return {
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
            }
        ],
        "mechanic": {
            "waiting_period_type": "INITIAL",
            "duration_value": 30,
            "duration_unit": "DAYS",
            "start_basis": "POLICY_INCEPTION",
            "applies_to": ["illness_treatment"],
            "exclusions_or_exceptions": ["accident_claims"],
            "modifications": [],
            "scope_type": "POLICY_WIDE",
            "value_source": "PRODUCT_FIXED",
            "member_waiting_basis": "POLICY_INCEPTION",
        },
    }


def _add_schedule_resolution(spec: dict) -> None:
    spec["evidence_selections"].append(
        {
            "role": "schedule_value_resolution",
            "document_id": "policy_wording_v1",
            "candidate_id": "candidate_page_53",
            "candidate_text_sha256": "def456",
        }
    )
    spec["mechanic"]["value_source"] = "POLICY_SCHEDULE_SELECTED"
    spec["mechanic"]["schedule_dependency"] = "Policy Schedule selects the duration."


def test_binds_product_fixed_scalar_wait_to_exact_primary_legal_candidate(tmp_path: Path) -> None:
    spec = _write_fixture(tmp_path)
    result = WaitingPeriodBinding().bind(
        spec=spec,
        repository_root=tmp_path,
        bound_at="2026-08-22T00:00:00+00:00",
    )
    assert result.manifest["binding_status"] == "reviewed_waiting_period_bound_not_published"
    assert result.manifest["resolution_status"] == "resolved_from_mechanism_evidence"
    assert result.manifest["mechanic"]["duration_value"] == 30
    assert result.manifest["mechanic"]["duration_unit"] == "DAYS"
    assert result.manifest["evidence"][0]["candidate_id"] == "candidate_page_21"
    assert result.manifest["publication_status"] == "bound_not_published"


def test_binds_schedule_selected_scalar_only_with_resolution_evidence(tmp_path: Path) -> None:
    spec = _write_fixture(tmp_path)
    _add_schedule_resolution(spec)

    result = WaitingPeriodBinding().bind(spec=spec, repository_root=tmp_path)

    assert result.manifest["resolution_status"] == "resolved_from_authoritative_schedule_evidence"
    assert result.manifest["mechanic"]["value_source"] == "POLICY_SCHEDULE_SELECTED"
    assert [item["role"] for item in result.manifest["evidence"]] == [
        "mechanism",
        "schedule_value_resolution",
    ]
    assert {item["candidate_id"] for item in result.manifest["evidence"]} == {
        "candidate_page_21",
        "candidate_page_53",
    }
    assert len(result.manifest["mechanic"]["evidence_reference_ids"]) == 2


def test_rejects_candidate_hash_mismatch(tmp_path: Path) -> None:
    spec = _write_fixture(tmp_path)
    spec["evidence_selections"][0]["candidate_text_sha256"] = "wrong"
    with pytest.raises(WaitingPeriodBindingError, match="candidate text hash mismatch"):
        WaitingPeriodBinding().bind(spec=spec, repository_root=tmp_path)


def test_rejects_schedule_resolution_hash_mismatch(tmp_path: Path) -> None:
    spec = _write_fixture(tmp_path)
    _add_schedule_resolution(spec)
    spec["evidence_selections"][1]["candidate_text_sha256"] = "wrong"
    with pytest.raises(WaitingPeriodBindingError, match="candidate text hash mismatch"):
        WaitingPeriodBinding().bind(spec=spec, repository_root=tmp_path)


def test_rejects_unresolved_schedule_selected_scalar(tmp_path: Path) -> None:
    spec = _write_fixture(tmp_path)
    spec["mechanic"]["value_source"] = "POLICY_SCHEDULE_SELECTED"
    spec["mechanic"]["schedule_dependency"] = "Policy Schedule selects the duration."
    with pytest.raises(WaitingPeriodBindingError, match="schedule_value_resolution"):
        WaitingPeriodBinding().bind(spec=spec, repository_root=tmp_path)


def test_rejects_schedule_resolution_for_product_fixed_mechanic(tmp_path: Path) -> None:
    spec = _write_fixture(tmp_path)
    spec["evidence_selections"].append(
        {
            "role": "schedule_value_resolution",
            "document_id": "policy_wording_v1",
            "candidate_id": "candidate_page_53",
            "candidate_text_sha256": "def456",
        }
    )
    with pytest.raises(WaitingPeriodBindingError, match="PRODUCT_FIXED"):
        WaitingPeriodBinding().bind(spec=spec, repository_root=tmp_path)


def test_rejects_non_primary_legal_source(tmp_path: Path) -> None:
    spec = _write_fixture(tmp_path)
    bundle = json.loads((tmp_path / "bundle.json").read_text(encoding="utf-8"))
    bundle["sources"][0]["authority_role"] = "discovery_only"
    (tmp_path / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
    with pytest.raises(WaitingPeriodBindingError, match="primary_legal"):
        WaitingPeriodBinding().bind(spec=spec, repository_root=tmp_path)
