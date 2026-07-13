from __future__ import annotations

import json
from pathlib import Path

from knowledge_domains.health.understanding_manufacturing.learning_path_manufacturing_line import (
    LearningPathManufacturingLine,
)


def primitive(
    primitive_type: str,
    *,
    primitive_id: str | None = None,
) -> dict:
    return {
        "primitive_id": primitive_id or f"lp_{primitive_type}",
        "primitive_type": primitive_type,
        "concept_id": "deductible",
        "concept_name": "Deductible",
        "learning_objective": f"Learn {primitive_type}.",
        "content": {"text": primitive_type},
        "delivery_tags": ["consumer", "learning"],
        "difficulty": "basic",
        "prerequisites": [],
        "evidence_refs": ["evidence_001"],
        "source_meaning_fields": ["core_meaning"],
        "confidence": 1.0,
        "review_status": "approved",
        "status": "certified_candidate",
    }


def collection(*, include_suitability: bool) -> dict:
    types = [
        "definition",
        "meaning",
        "purpose",
        "money_flow",
        "worked_example",
        "misconception",
        "related_concepts",
        "faq",
    ]
    if include_suitability:
        types.append("suitability")

    return {
        "asset_id": "lpc_test",
        "asset_type": "learning_primitive_collection",
        "collection_id": "lpc_test",
        "collection_version": "1.0",
        "schema_version": "learning_primitive_collection_v1.0",
        "department_boundary": (
            "meaning_to_learning_primitives_only_no_personalized_advice"
        ),
        "concept_id": "deductible",
        "concept_name": "Deductible",
        "source_meaning_asset_id": "meaning_deductible_test",
        "source_meaning_asset_type": "meaning_asset",
        "primitives": [primitive(item) for item in types],
        "notes": [],
    }


def run_line(tmp_path: Path, *, include_suitability: bool) -> tuple[dict, dict]:
    input_path = tmp_path / "input.json"
    output_dir = tmp_path / "out"
    input_path.write_text(
        json.dumps(collection(include_suitability=include_suitability)),
        encoding="utf-8",
    )

    result = LearningPathManufacturingLine(
        input_path=input_path,
        output_dir=output_dir,
        factory_version="1.0",
    ).run()

    asset = json.loads(Path(result["asset"]).read_text(encoding="utf-8"))
    certification = json.loads(
        Path(result["certification"]).read_text(encoding="utf-8")
    )
    return asset, certification


def test_educational_collection_excludes_buying_decision(tmp_path):
    asset, certification = run_line(
        tmp_path,
        include_suitability=False,
    )
    path_types = {path["path_type"] for path in asset["paths"]}

    assert "buying_decision" not in path_types
    assert certification["validation_status"] == "passed"
    assert "recommendation_boundary_preserved" in certification["gates_passed"]


def test_educational_collection_has_no_recommendation_tags_or_navigation(
    tmp_path,
):
    asset, _ = run_line(tmp_path, include_suitability=False)

    for path in asset["paths"]:
        assert "recommendation" not in path.get("tags", [])
        assert "purchase" not in path.get("tags", [])
        assert "buying_decision" not in path.get(
            "recommended_next_paths", []
        )


def test_deep_learning_does_not_warn_about_missing_suitability(tmp_path):
    asset, _ = run_line(tmp_path, include_suitability=False)
    deep = next(
        path
        for path in asset["paths"]
        if path["path_type"] == "deep_learning"
    )

    assert all(
        "suitability" not in warning.lower()
        for warning in deep.get("warnings", [])
    )


def test_suitability_collection_preserves_legacy_buying_path(tmp_path):
    asset, certification = run_line(
        tmp_path,
        include_suitability=True,
    )
    path_types = {path["path_type"] for path in asset["paths"]}

    assert "buying_decision" in path_types
    assert certification["validation_status"] == "passed"
