from pathlib import Path
import json

from knowledge_domains.health.understanding_manufacturing.learning_path_manufacturing_line import (
    LearningPathManufacturingLine,
)


FIXTURE = Path("tests/department_05/fixtures/copay_learning_primitive_collection.json")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_copay_learning_paths_are_manufactured(tmp_path):
    result = LearningPathManufacturingLine(input_path=FIXTURE, output_dir=tmp_path).run()

    asset = load_json(result["asset"])
    certification = load_json(result["certification"])
    report = load_json(result["report"])

    assert asset["asset_type"] == "learning_path_collection"
    assert asset["concept_id"] == "copay"
    assert asset["department_boundary"] == "learning_primitives_to_learning_paths_only_no_new_content_no_personalization"
    assert len(asset["paths"]) == 5
    assert certification["validation_status"] == "passed"
    assert "standard_paths_manufactured" in certification["gates_passed"]
    assert "steps_reference_existing_primitives" in certification["gates_passed"]
    assert report["statistics"]["path_count"] == 5


def test_claim_path_uses_expected_copay_primitives(tmp_path):
    result = LearningPathManufacturingLine(input_path=FIXTURE, output_dir=tmp_path).run()
    asset = load_json(result["asset"])

    claim_path = [p for p in asset["paths"] if p["path_type"] == "claim_understanding"][0]
    primitive_types = [step["primitive_type"] for step in claim_path["steps"]]

    assert primitive_types == [
        "definition",
        "meaning",
        "money_flow",
        "worked_example",
        "misconception",
        "faq",
    ]
    assert claim_path["target_persona"] == "consumer"
    assert claim_path["delivery_context"] == "claim_confusion"


def test_path_steps_reference_existing_primitives(tmp_path):
    result = LearningPathManufacturingLine(input_path=FIXTURE, output_dir=tmp_path).run()
    asset = load_json(result["asset"])
    primitive_asset = load_json(FIXTURE)

    primitive_ids = {p["primitive_id"] for p in primitive_asset["primitives"]}
    for path in asset["paths"]:
        seen = set()
        for expected_step, step in enumerate(path["steps"], start=1):
            assert step["step_number"] == expected_step
            assert step["primitive_id"] in primitive_ids
            assert step["primitive_id"] not in seen
            seen.add(step["primitive_id"])


def test_deterministic_learning_path_asset_id(tmp_path):
    first = LearningPathManufacturingLine(input_path=FIXTURE, output_dir=tmp_path / "a").run()
    second = LearningPathManufacturingLine(input_path=FIXTURE, output_dir=tmp_path / "b").run()

    first_asset = load_json(first["asset"])
    second_asset = load_json(second["asset"])

    assert first_asset["asset_id"] == second_asset["asset_id"]
    assert first_asset["paths"] == second_asset["paths"]
