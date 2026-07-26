from pathlib import Path

from knowledge_factory.decision_intelligence.decision_intelligence_asset_builder import (
    DecisionIntelligenceAssetBuilder,
)


def test_asset_builder(tmp_path: Path):

    outputs = DecisionIntelligenceAssetBuilder(
        tmp_path
    ).build("copay")

    assert outputs["status"] == "PASS"
    assert outputs["score"] == 100