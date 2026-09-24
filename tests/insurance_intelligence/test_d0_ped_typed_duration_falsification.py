from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLICATION = (
    ROOT
    / "knowledge/factory/registry_backed/star_health_star_comprehensive/publication"
    / "ped_waiting_period_authoritative_publication.json"
)


def test_ped_duration_publication_carries_typed_value_and_unit() -> None:
    publication = json.loads(PUBLICATION.read_text(encoding="utf-8"))
    duration = next(
        item
        for item in publication["semantic_components"]
        if item["component_id"] == "waiting_period_duration"
    )
    attributes = {
        item["key"]: item["value"]
        for item in duration.get("semantic_attributes", [])
    }

    assert attributes["duration_value"] == "36"
    assert attributes["duration_unit"] == "MONTHS"
