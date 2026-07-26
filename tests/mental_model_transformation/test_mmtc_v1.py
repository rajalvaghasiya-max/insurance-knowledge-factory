import json
from pathlib import Path

from knowledge_domains.health.mental_model_transformation.stations.incoming_inspection_station import IncomingInspectionStation
from knowledge_domains.health.mental_model_transformation.stations.current_model_detection_station import CurrentModelDetectionStation
from knowledge_domains.health.mental_model_transformation.stations.target_model_station import TargetModelStation
from knowledge_domains.health.mental_model_transformation.stations.knowledge_gap_station import KnowledgeGapStation
from knowledge_domains.health.mental_model_transformation.stations.transformation_planning_station import TransformationPlanningStation
from knowledge_domains.health.mental_model_transformation.mental_model_transformation_line import MentalModelTransformationLine


SAMPLE = Path("knowledge/factory/distillation/reports/kdr_f825201b784b9e3aec125417_distillation_report.json")


def load_sample():
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def test_incoming_inspection_accepts_mma_opportunity():
    report = load_sample()
    result = IncomingInspectionStation().inspect(report)
    assert result["pass"] is True
    assert "mental_model_asset" in result["opportunities"]


def test_current_model_detection_detects_total_bill_misconception():
    blueprint = IncomingInspectionStation().manufacture(load_sample())
    blueprint = CurrentModelDetectionStation().manufacture(blueprint)
    assert "total hospital bill" in blueprint.current_model.belief


def test_gap_and_plan_are_built_for_admissible_claim():
    blueprint = IncomingInspectionStation().manufacture(load_sample())
    blueprint = CurrentModelDetectionStation().manufacture(blueprint)
    blueprint = TargetModelStation().manufacture(blueprint)
    blueprint = KnowledgeGapStation().manufacture(blueprint)
    assert "admissible_claim" in blueprint.knowledge_gap.missing_concepts
    blueprint = TransformationPlanningStation().manufacture(blueprint)
    assert blueprint.transformation_plan.transformation_type == "Correction"


def test_line_manufactures_one_asset(tmp_path):
    line = MentalModelTransformationLine(output_root=tmp_path / "mental_models")
    result = line.manufacture_from_report(load_sample())
    assert result is not None
    asset = json.loads(Path(result["asset"]).read_text(encoding="utf-8"))
    assert asset["concept_id"] == "copay"
    assert asset["certification_status"] == "PASS"
    assert asset["knowledge_gap"]["missing_concepts"]
