from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_reassure3_registration_execution_preserves_v2_cold_start_boundary() -> None:
    path = ROOT / "docs/architecture/niva_bupa_reassure_3_0_generic_registration_execution_2026-08-24.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["product"]["uin"] == "NBHHLIP26047V012526"
    assert data["source"]["source_sha256"] == "04c06f045979be509e124e1d802fed47097f0995132ff94cfd67aafbaf2fa12f"
    assert data["source"]["candidate_count"] == 62
    assert data["execution"]["registration_status"] == "generic_sources_registered_evidence_review_required"
    assert data["repeatability_boundary"]["frozen_runtime_changes"] == 0
    assert data["repeatability_boundary"]["target_concepts_scored"] is False
    assert data["governance"]["registration_success_does_not_imply_certification"] is True
