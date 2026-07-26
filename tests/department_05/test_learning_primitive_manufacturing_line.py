from pathlib import Path
import json

from knowledge_domains.health.understanding_manufacturing.learning_primitive_manufacturing_line import (
    LearningPrimitiveManufacturingLine,
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_copay_learning_primitives_are_manufactured(tmp_path):
    input_path = Path("knowledge/factory/meaning_assets/copay_meaning_asset.json")
    result = LearningPrimitiveManufacturingLine(input_path=input_path, output_dir=tmp_path).run()

    asset = load_json(result["asset"])
    certification = load_json(result["certification"])
    report = load_json(result["report"])

    assert asset["asset_type"] == "learning_primitive_collection"
    assert asset["concept_id"] == "copay"
    assert asset["department_boundary"] == "meaning_to_learning_primitives_only_no_personalized_advice"
    assert len(asset["primitives"]) >= 10
    assert certification["validation_status"] == "passed"
    assert "learning_objectives_present" in certification["gates_passed"]
    assert "traceability_preserved" in certification["gates_passed"]
    assert report["statistics"]["primitive_type_counts"]["worked_example"] == 1


def test_worked_example_preserves_correct_copay_math(tmp_path):
    input_path = Path("knowledge/factory/meaning_assets/copay_meaning_asset.json")
    result = LearningPrimitiveManufacturingLine(input_path=input_path, output_dir=tmp_path).run()
    asset = load_json(result["asset"])

    worked = [p for p in asset["primitives"] if p["primitive_type"] == "worked_example"][0]
    content = worked["content"]

    assert content["hospital_bill"] == 100000
    assert content["approved_claim_amount"] == 90000
    assert content["non_payable_amount"] == 10000
    assert content["copay_amount"] == 18000
    assert content["customer_pays_total"] == 28000
    assert content["insurer_pays"] == 72000


def test_deterministic_asset_id(tmp_path):
    input_path = Path("knowledge/factory/meaning_assets/copay_meaning_asset.json")
    first = LearningPrimitiveManufacturingLine(input_path=input_path, output_dir=tmp_path / "a").run()
    second = LearningPrimitiveManufacturingLine(input_path=input_path, output_dir=tmp_path / "b").run()

    first_asset = load_json(first["asset"])
    second_asset = load_json(second["asset"])

    assert first_asset["asset_id"] == second_asset["asset_id"]
    assert first_asset["primitives"] == second_asset["primitives"]
