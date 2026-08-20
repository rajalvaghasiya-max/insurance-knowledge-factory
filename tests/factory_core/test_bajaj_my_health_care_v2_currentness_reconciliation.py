from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from factory_core.governance.document_currentness_evidence import (
    DocumentCurrentnessEvidenceError,
    DocumentCurrentnessEvidenceRecord,
)
from factory_core.governance.source_observation import SourceObservationRecord


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ARCH = REPOSITORY_ROOT / "docs" / "architecture"

CURRENT_SHA = "05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158"
HISTORICAL_SHA = "9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade"
V2_REGISTRATION_PATH = (
    "knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/"
    "v2/generic_source_registration/policy_wording_registration.json"
)
SOURCE_OBSERVATION_OUTPUT = (
    "knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/"
    "v2/governance/bajaj_my_health_care_v2_source_observation_20260820.json"
)
CURRENTNESS_EVIDENCE_OUTPUT = (
    "knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/"
    "v2/governance/bajaj_my_health_care_v2_currentness_evidence_20260820.json"
)


def _load(name: str) -> dict:
    return json.loads((ARCH / name).read_text(encoding="utf-8"))


def test_v2_currentness_specs_bind_only_exact_registered_version() -> None:
    registration = _load("bajaj_my_health_care_current_version_generic_sources_registration_spec.json")
    observation = _load("bajaj_my_health_care_v2_source_observation_2026-08-20_spec.json")
    evidence = _load("bajaj_my_health_care_v2_currentness_evidence_2026-08-20_spec.json")
    overlay = _load("bajaj_my_health_care_current_version_document_identity_resolution_spec.json")
    capture = _load("bajaj_my_health_care_v2_currentness_capture_2026-08-20.json")

    document = registration["documents"][0]
    assert document["source_document_id"] == CURRENT_SHA
    assert HISTORICAL_SHA not in document["document_path"]
    assert observation["registered_document"]["registration_path"] == V2_REGISTRATION_PATH
    assert observation["observation"]["observed_pdf_sha256"] == CURRENT_SHA
    assert CURRENT_SHA in observation["observation"]["observed_pdf_path"]
    assert evidence["registered_document"]["registration_path"] == V2_REGISTRATION_PATH
    assert evidence["source_observation"]["observation_record_path"] == SOURCE_OBSERVATION_OUTPUT
    assert overlay["documents"][0]["registration_path"] == V2_REGISTRATION_PATH
    assert overlay["documents"][0]["currentness_evidence_path"] == CURRENTNESS_EVIDENCE_OUTPUT
    assert capture["registration_binding"]["expected_registered_sha256"] == CURRENT_SHA


def test_v1_remains_immutable_and_copayment_remains_blocked() -> None:
    reconciliation = _load("bajaj_my_health_care_version_reconciliation_2026-08-18.json")
    capture = _load("bajaj_my_health_care_v2_currentness_capture_2026-08-20.json")

    assert reconciliation["historical_version"]["sha256"] == HISTORICAL_SHA
    assert reconciliation["observed_current_version"]["sha256"] == CURRENT_SHA
    assert reconciliation["governance_decision"]["historical_artifact"] == (
        "retain_immutable_historical_version"
    )
    assert capture["governance_boundary"]["copayment_manufacturing"] == "BLOCKED"
    assert capture["governance_boundary"]["auto_publication"] == "PROHIBITED"
    assert capture["governance_boundary"]["architecture_change"] == "NONE"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _registration(root: Path, content_sha: str) -> str:
    relative = "knowledge/factory/registry_backed/test_product/v2/generic_source_registration/policy_wording_registration.json"
    _write_json(
        root / relative,
        {
            "document": {
                "document_id": "bajaj_my_health_care_policy_wording_v2",
                "document_version_id": "docver_bajaj_v2_test",
                "document_type": "policy_wording",
                "content_sha256": content_sha,
            }
        },
    )
    return relative


def _source_observation_spec(registration_path: str, pdf_path: str, page_path: str) -> dict:
    return {
        "schema_version": "1.0",
        "record_type": "source_observation_record_v1",
        "observation_id": "bajaj_v2_contract_regression",
        "registered_document": {"registration_path": registration_path},
        "observation": {
            "retrieval_status": "succeeded",
            "source_url": "https://www.bajajgeneralinsurance.com/example/policy.pdf",
            "source_url_key": "https://www.bajajgeneralinsurance.com/example/policy.pdf",
            "source_page_url": "https://www.bajajgeneralinsurance.com/example/documents.html",
            "source_page_artifact_path": page_path,
            "observed_at": "2026-08-20T22:14:00+05:30",
            "http_status": 200,
            "content_type": "application/pdf",
            "capture_strategy": "test_fixture",
            "observed_pdf_path": pdf_path,
        },
        "source_signals": {
            "source_issued_label": None,
            "effective_date_signal": None,
            "version_signal": "BAJHLIP26074V022526",
        },
    }


def _currentness_spec(registration_path: str, observation_path: str) -> dict:
    return {
        "schema_version": "1.0",
        "record_type": "document_currentness_evidence_record_v1",
        "reviewed_by_human": True,
        "registered_document": {"registration_path": registration_path},
        "source_observation": {"observation_record_path": observation_path},
        "evidence_items": [
            {
                "evidence_type": "official_product_page_document_link",
                "evidence_status": "supports_currentness_review",
                "verification": "retained_official_html_manual_review",
                "observed_text": "Official page links the observed policy wording.",
                "evidence_reference": "archive/web/source_page.html",
                "linked_document_url": "https://www.bajajgeneralinsurance.com/example/policy.pdf",
                "link_label": "Policy Wording",
            }
        ],
        "reviewed_at": "2026-08-20T22:14:00+05:30",
        "review_rationale": "Regression fixture for Bajaj v2 currentness fail-closed behavior.",
    }


def test_changed_live_bytes_cannot_support_currentness(tmp_path: Path) -> None:
    registered_bytes = b"registered-v2-bytes"
    observed_bytes = b"changed-live-bytes"
    registration_path = _registration(tmp_path, _sha(registered_bytes))
    pdf_rel = "archive/raw_pdf/observed.pdf"
    page_rel = "archive/web/source_page.html"
    (tmp_path / pdf_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / pdf_rel).write_bytes(observed_bytes)
    (tmp_path / page_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / page_rel).write_text("official page", encoding="utf-8")

    observation = SourceObservationRecord().build(
        spec=_source_observation_spec(registration_path, pdf_rel, page_rel),
        repository_root=tmp_path,
        recorded_at="2026-08-20T22:14:00+05:30",
    )
    assert observation.record["byte_comparison"]["status"] == "bytes_changed_observed"

    observation_rel = "knowledge/factory/registry_backed/test_product/v2/governance/observation.json"
    _write_json(tmp_path / observation_rel, dict(observation.record))

    with pytest.raises(
        DocumentCurrentnessEvidenceError,
        match="byte_identical_observed",
    ):
        DocumentCurrentnessEvidenceRecord().build(
            spec=_currentness_spec(registration_path, observation_rel),
            repository_root=tmp_path,
            recorded_at="2026-08-20T22:14:00+05:30",
        )


def test_missing_retained_source_page_fails_closed(tmp_path: Path) -> None:
    observed_bytes = b"byte-identical-v2-fixture"
    registration_path = _registration(tmp_path, _sha(observed_bytes))
    pdf_rel = "archive/raw_pdf/observed.pdf"
    page_rel = "archive/web/source_page.html"
    (tmp_path / pdf_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / pdf_rel).write_bytes(observed_bytes)
    (tmp_path / page_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / page_rel).write_text("official page", encoding="utf-8")

    observation = SourceObservationRecord().build(
        spec=_source_observation_spec(registration_path, pdf_rel, page_rel),
        repository_root=tmp_path,
        recorded_at="2026-08-20T22:14:00+05:30",
    )
    assert observation.record["byte_comparison"]["status"] == "byte_identical_observed"

    observation_rel = "knowledge/factory/registry_backed/test_product/v2/governance/observation.json"
    _write_json(tmp_path / observation_rel, dict(observation.record))
    (tmp_path / page_rel).unlink()

    with pytest.raises(
        DocumentCurrentnessEvidenceError,
        match="source page artifact was not found",
    ):
        DocumentCurrentnessEvidenceRecord().build(
            spec=_currentness_spec(registration_path, observation_rel),
            repository_root=tmp_path,
            recorded_at="2026-08-20T22:14:00+05:30",
        )
