from __future__ import annotations

import json
from pathlib import Path

from factory_sdk import stable_hash
from knowledge_domains.health.understanding_manufacturing.understanding_asset_manufacturing_line import (
    UnderstandingAssetManufacturingLine,
)


FIXTURES = Path(__file__).parent / "fixtures"


def _run(tmp_path: Path):
    return UnderstandingAssetManufacturingLine(
        meaning_asset_path=FIXTURES / "copay_meaning_asset.json",
        learning_primitive_asset_path=FIXTURES / "copay_learning_primitive_collection.json",
        learning_path_asset_path=FIXTURES / "copay_learning_path_collection.json",
        output_dir=tmp_path,
    ).run()


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_understanding_asset_manufactures_certified_package(tmp_path: Path):
    result = _run(tmp_path)
    asset = _load(result["asset"])
    certification = _load(result["certification"])

    assert asset["asset_type"] == "understanding_asset"
    assert asset["concept_id"] == "copay"
    assert asset["learning_primitives"]["count"] == 11
    assert asset["learning_paths"]["count"] == 5
    assert len(asset["learning_outcomes"]) >= 10
    assert certification["validation_status"] == "passed"
    assert certification["quality_score"] == 100.0


def test_understanding_asset_preserves_traceability(tmp_path: Path):
    result = _run(tmp_path)
    asset = _load(result["asset"])

    traceability = asset["traceability"]
    assert traceability["meaning_asset_id"] == "meaning_copay_v1"
    assert traceability["learning_primitive_collection_id"] == "lpc_ac06c8787c34ca45b248bc12"
    assert traceability["learning_path_collection_id"] == "lpathc_98228ee122871e2a4dafef9b"
    assert "manual_golden_copay_example_v1" in traceability["source_evidence_refs"]


def test_understanding_asset_preserves_department_boundary(tmp_path: Path):
    result = _run(tmp_path)
    asset = _load(result["asset"])
    report = _load(result["report"])

    expected_boundary = "meaning_primitives_paths_to_understanding_asset_only_no_new_content_no_personalization"
    assert asset["department_boundary"] == expected_boundary
    assert report["department_boundary"] == expected_boundary
    assert asset["notes"][1].startswith("No new educational content")


def test_understanding_asset_factory_signature_present(tmp_path: Path):
    result = _run(tmp_path)
    asset = _load(result["asset"])

    signature = asset["factory_signature"]
    assert signature["factory"] == "PolicyScna Knowledge Factory"
    assert signature["department"] == "department_05_understanding_manufacturing"
    assert signature["production_line"] == "UnderstandingAssetManufacturingLine"
    assert signature["deterministic"] is True


def test_understanding_asset_output_is_deterministic(tmp_path: Path):
    result_one = _run(tmp_path / "one")
    result_two = _run(tmp_path / "two")

    asset_one = _load(result_one["asset"])
    asset_two = _load(result_two["asset"])

    assert asset_one["asset_id"] == asset_two["asset_id"]
    assert stable_hash(asset_one) == stable_hash(asset_two)
