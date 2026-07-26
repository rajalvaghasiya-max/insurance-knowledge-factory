from __future__ import annotations

import json
from pathlib import Path

from knowledge_domains.health.understanding.understanding_asset_builder import CopayUnderstandingAssetBuilder
from knowledge_domains.health.understanding.understanding_certification_engine import UnderstandingCertificationEngine


def test_copay_understanding_asset_certifies_pass() -> None:
    builder = CopayUnderstandingAssetBuilder()
    asset = builder.build()
    assert asset.concept_id == "copay"
    assert asset.certification_status == "PASS"
    assert asset.certification["score"] == 100


def test_copay_understanding_asset_contains_required_sections() -> None:
    asset = CopayUnderstandingAssetBuilder().build().to_dict()
    required = [
        "reality",
        "common_misunderstanding",
        "root_causes",
        "consequence",
        "example",
        "expectation_gap",
        "golden_rule",
        "transformation",
        "verification",
    ]
    for key in required:
        assert asset[key]


def test_copay_verification_math() -> None:
    asset = CopayUnderstandingAssetBuilder().build()
    example = asset.example
    assert example["hospital_bill"] - example["non_medical_expenses"] == example["admissible_claim"]
    assert example["admissible_claim"] * example["copay_percent"] / 100 == example["copay_amount"]
    assert asset.verification["expected_answer"] == 45000
    assert asset.verification["common_wrong_answer"] == 50000


def test_outputs_written_to_gcp_discoverable_path(tmp_path: Path) -> None:
    outputs = CopayUnderstandingAssetBuilder().write_outputs(tmp_path)
    asset_path = Path(outputs["asset"])
    assert asset_path.exists()
    assert "knowledge/factory/golden_concepts/copay/understanding_assets" in asset_path.as_posix()
    data = json.loads(asset_path.read_text(encoding="utf-8"))
    assert data["certification_status"] == "PASS"
