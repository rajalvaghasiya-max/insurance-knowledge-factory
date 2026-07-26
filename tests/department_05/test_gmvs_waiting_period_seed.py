"""GMVS-001 seed validation tests.

These tests validate the Waiting Period golden meaning asset shape.
They do not require running the full Department V pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path


WAITING_PERIOD_MEANING = Path(
    "knowledge/factory/golden_concepts/waiting_period/waiting_period_meaning_asset.json"
)


def test_waiting_period_meaning_asset_exists() -> None:
    assert WAITING_PERIOD_MEANING.exists()


def test_waiting_period_meaning_asset_contract() -> None:
    payload = json.loads(WAITING_PERIOD_MEANING.read_text(encoding="utf-8"))
    assert payload["asset_type"] == "meaning_asset"
    assert payload["concept_id"] == "waiting_period"
    assert payload["canonical_name"] == "Waiting Period"
    assert payload["core_meaning"]
    assert payload["business_purpose"]
    assert payload["functional_behaviour"]
    assert payload["calculation_basis"]
    assert payload["misinterpretations"]
    assert payload["policy_examples"]


def test_waiting_period_tests_time_pattern() -> None:
    payload = json.loads(WAITING_PERIOD_MEANING.read_text(encoding="utf-8"))
    combined = " ".join(
        [
            payload.get("calculation_basis", ""),
            " ".join(payload.get("inputs", [])),
            " ".join(payload.get("outputs", [])),
        ]
    ).lower()
    assert "date" in combined
    assert "waiting_period_duration" in combined
