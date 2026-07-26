from __future__ import annotations

import json
from pathlib import Path

from factory_sdk.golden_concept_pipeline import GoldenConceptManufacturingPipeline
from factory_sdk.golden_concept_pipeline.production_cell_registry import ProductionCellRegistry
from factory_sdk.golden_concept_pipeline.production_cells import FoundationPassthroughCell, MentalModelTransformationCellAdapter


ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "knowledge" / "factory" / "distillation" / "reports"


def test_registry_registers_cells():
    registry = ProductionCellRegistry()
    registry.register("knowledge_asset", FoundationPassthroughCell())
    registry.register("mental_model_asset", MentalModelTransformationCellAdapter())

    data = registry.to_dict()["registered_cells"]
    assert "knowledge_asset" in data
    assert "mental_model_asset" in data
    assert registry.is_available("mental_model_asset")


def test_gcmp_v2_executes_mmtc(tmp_path):
    pipeline = GoldenConceptManufacturingPipeline()
    outputs = pipeline.run_from_dir(
        distillation_dir=REPORTS_DIR,
        concept_id="copay",
        output_dir=tmp_path / "golden_concepts" / "copay",
    )

    state = json.loads(Path(outputs["manufacturing_state"]).read_text(encoding="utf-8"))
    execution = json.loads(Path(outputs["execution_log"]).read_text(encoding="utf-8"))

    pass_items = [item for item in state["items"] if item["status"] == "PASS"]
    assert any(item["asset_type"] == "mental_model_asset" for item in pass_items)
    assert any(result["production_cell"] == "mental_model_transformation_cell" for result in execution["results"])

    mental_model_item = next(item for item in state["items"] if item["asset_type"] == "mental_model_asset")
    assert "asset" in mental_model_item["output_paths"]
    assert Path(mental_model_item["output_paths"]["asset"]).exists()


def test_foundation_dependencies_are_marked_available(tmp_path):
    pipeline = GoldenConceptManufacturingPipeline()
    outputs = pipeline.run_from_dir(
        distillation_dir=REPORTS_DIR,
        concept_id="copay",
        output_dir=tmp_path / "golden_concepts" / "copay",
    )
    state = json.loads(Path(outputs["manufacturing_state"]).read_text(encoding="utf-8"))

    foundation_items = [item for item in state["items"] if item["asset_type"] in {"knowledge_asset", "understanding_gap"}]
    assert foundation_items
    assert all(item["status"] == "PASS" for item in foundation_items)


def test_execution_outputs_are_written(tmp_path):
    pipeline = GoldenConceptManufacturingPipeline()
    outputs = pipeline.run_from_dir(
        distillation_dir=REPORTS_DIR,
        concept_id="copay",
        output_dir=tmp_path / "golden_concepts" / "copay",
    )

    assert outputs["execution_log"].exists()
    assert outputs["manufacturing_state"].exists()
    assert outputs["production_cell_registry"].exists()
