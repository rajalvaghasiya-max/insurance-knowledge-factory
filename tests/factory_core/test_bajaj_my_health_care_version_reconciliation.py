from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RECONCILIATION = REPOSITORY_ROOT / "docs" / "architecture" / "bajaj_my_health_care_version_reconciliation_2026-08-18.json"
MANIFEST = REPOSITORY_ROOT / "docs" / "architecture" / "bajaj_my_health_care_current_version_migration_manifest.json"

HISTORICAL_SHA = "9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade"
CURRENT_SHA = "05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_bajaj_version_reconciliation_preserves_history_and_blocks_copayment() -> None:
    record = _load(RECONCILIATION)

    assert record["review_status"] == "MATERIAL_REVISION_CONFIRMED"
    assert record["historical_version"]["sha256"] == HISTORICAL_SHA
    assert record["observed_current_version"]["sha256"] == CURRENT_SHA
    assert record["comparison"]["pdf_byte_match"] is False
    assert record["comparison"]["normalized_text_match"] is False
    assert record["governance_decision"]["historical_artifact"] == "retain_immutable_historical_version"
    assert record["governance_decision"]["current_artifact"] == "register_as_separate_document_version"
    assert record["governance_decision"]["copayment_manufacturing"] == "BLOCKED"
    assert record["governance_decision"]["architecture_change"] == "NONE"


def test_bajaj_current_version_manifest_binds_the_new_sha_not_the_historical_sha() -> None:
    manifest = _load(MANIFEST)

    assert manifest["expected_source_sha256"] == CURRENT_SHA
    assert HISTORICAL_SHA not in manifest["expected_source_path"]
    assert manifest["entity_id"] == "bajaj_allianz_general:my_health_care"
    assert manifest["specs"]["overlay"].endswith("current_version_document_identity_resolution_spec.json")
