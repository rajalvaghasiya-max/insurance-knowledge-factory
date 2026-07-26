
from __future__ import annotations

import json
from pathlib import Path

from knowledge_domains.health.understanding_manufacturing.learning_path_manufacturing_line import (
    LearningPathManufacturingLine,
)


def primitive(primitive_type: str) -> dict:
    return {
        "primitive_id": f"lp_{primitive_type}",
        "primitive_type": primitive_type,
        "concept_id": "copay",
        "concept_name": "Copay",
        "learning_objective": f"Learn {primitive_type}.",
        "content": {"text": primitive_type},
        "delivery_tags": ["consumer", "learning"],
        "difficulty": "basic",
        "prerequisites": [],
        "evidence_refs": ["copay_evidence_001"],
        "source_meaning_fields": ["core_meaning"],
        "confidence": 1.0,
        "review_status": "approved",
        "status": "certified_candidate",
    }


def collection(types: list[str]) -> dict:
    return {
        "asset_id": "lpc_copay_governed_test",
        "asset_type": "learning_primitive_collection",
        "collection_id": "lpc_copay_governed_test",
        "collection_version": "1.0",
        "schema_version": "learning_primitive_collection_v1.0",
        "department_boundary": (
            "meaning_to_learning_primitives_only_no_personalized_advice"
        ),
        "concept_id": "copay",
        "concept_name": "Copay",
        "source_meaning_asset_id": "meaning_copay_governed_test",
        "source_meaning_asset_type": "meaning_asset",
        "primitives": [primitive(item) for item in types],
        "notes": [],
    }


def run_line(tmp_path: Path, types: list[str]) -> tuple[dict, dict]:
    input_path = tmp_path / "input.json"
    output_dir = tmp_path / "out"
    input_path.write_text(
        json.dumps(collection(types)),
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


def governed_types() -> list[str]:
    return [
        "definition",
        "meaning",
        "purpose",
        "money_flow",
        "worked_example",
        "misconception",
        "related_concepts",
        "faq",
    ]


def test_governed_paths_do_not_warn_for_optional_enrichment_primitives(
    tmp_path: Path,
) -> None:
    asset, certification = run_line(tmp_path, governed_types())

    for path in asset["paths"]:
        warning_text = " ".join(path.get("warnings", [])).lower()
        assert "advisor_note" not in warning_text
        assert "source_example" not in warning_text
        assert "suitability" not in warning_text

    assert certification["validation_status"] == "passed"
    assert certification["warnings"] == []


def test_deep_learning_does_not_claim_comparison_without_suitability(
    tmp_path: Path,
) -> None:
    asset, _ = run_line(tmp_path, governed_types())
    deep = next(
        path
        for path in asset["paths"]
        if path["path_type"] == "deep_learning"
    )
    criteria = " ".join(deep["success_criteria"]).lower()

    assert "compare" not in criteria
    assert "define, explain, calculate, and teach" in criteria


def test_compare_criterion_is_preserved_when_suitability_exists(
    tmp_path: Path,
) -> None:
    types = governed_types() + ["suitability"]
    asset, certification = run_line(tmp_path, types)
    deep = next(
        path
        for path in asset["paths"]
        if path["path_type"] == "deep_learning"
    )
    criteria = " ".join(deep["success_criteria"]).lower()

    assert "compare" in criteria
    assert certification["validation_status"] == "passed"


def test_real_path_warnings_propagate_to_certification(
    tmp_path: Path,
) -> None:
    types = [item for item in governed_types() if item != "definition"]
    asset, certification = run_line(tmp_path, types)

    assert any(path.get("warnings") for path in asset["paths"])
    assert certification["validation_status"] == "needs_review"
    assert certification["warnings"]
    warning_text = json.dumps(
        certification["warnings"],
        ensure_ascii=False,
    ).lower()
    assert "missing mandatory primitive type" in warning_text
    assert certification["quality_score"] == 95.0
