import json
from pathlib import Path

from factory_sdk.golden_concept_pipeline import GoldenConceptManufacturingPipeline
from factory_sdk.golden_concept_pipeline.report_reader import DistillationReportReader
from factory_sdk.golden_concept_pipeline.manufacturing_queue import ManufacturingQueueBuilder
from factory_sdk.golden_concept_pipeline.dependency_resolver import DependencyResolver


def sample_report(asset_types):
    return {
        "distillation_id": "kdr_test001",
        "observation": {
            "observation_id": "COPAY-OBS-001",
            "concept_id": "copay",
            "title": "Customer calculates Copay on total hospital bill",
        },
        "knowledge_potential": {"overall": 9.0},
        "manufacturing_opportunities": [
            {
                "asset_type": asset_type,
                "reason": f"Need {asset_type}",
                "priority": "high",
                "target_department": "MMTS" if asset_type == "mental_model_asset" else "Department V",
            }
            for asset_type in asset_types
        ],
        "relationships": ["copay", "admissible_claim"],
        "confidence": 0.97,
        "review_required": True,
    }


def write_report(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / f"{data['distillation_id']}_distillation_report.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_reader_reads_kde_report(tmp_path):
    path = write_report(tmp_path, sample_report(["mental_model_asset"]))
    report = DistillationReportReader().read_file(path)
    assert report.concept_id == "copay"
    assert report.opportunities[0].asset_type == "mental_model_asset"


def test_queue_builder_groups_duplicate_asset_types(tmp_path):
    path1 = write_report(tmp_path, sample_report(["financial_simulation"]))
    data2 = sample_report(["financial_simulation"])
    data2["distillation_id"] = "kdr_test002"
    data2["observation"]["observation_id"] = "COPAY-OBS-002"
    path2 = write_report(tmp_path, data2)
    reports = DistillationReportReader().read_dir(tmp_path, concept_id="copay")
    queue = ManufacturingQueueBuilder().build(reports, "copay")
    assert len(queue.tasks) == 1
    assert queue.tasks[0].asset_type == "financial_simulation"
    assert len(queue.tasks[0].source_distillation_ids) == 2


def test_dependency_resolver_adds_foundation_tasks(tmp_path):
    path = write_report(tmp_path, sample_report(["financial_simulation"]))
    reports = DistillationReportReader().read_dir(tmp_path, concept_id="copay")
    raw_queue = ManufacturingQueueBuilder().build(reports, "copay")
    queue, graph = DependencyResolver().resolve(raw_queue)
    asset_types = {t.asset_type for t in queue.tasks}
    assert "knowledge_asset" in asset_types
    assert "understanding_gap" in asset_types
    assert "financial_simulation" in asset_types
    assert {"from": "knowledge_asset", "to": "understanding_gap"} in graph.edges


def test_pipeline_writes_package_and_certification(tmp_path):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    write_report(reports_dir, sample_report(["mental_model_asset", "financial_simulation", "golden_rule"]))
    output_dir = tmp_path / "golden" / "copay"
    outputs = GoldenConceptManufacturingPipeline().run_from_dir(
        distillation_dir=reports_dir,
        concept_id="copay",
        output_dir=output_dir,
    )
    assert outputs["manufacturing_queue"].exists()
    assert outputs["dependency_graph"].exists()
    assert outputs["dispatch_plan"].exists()
    assert outputs["golden_concept_package"].exists()
    assert outputs["certification"].exists()
    cert = json.loads(outputs["certification"].read_text(encoding="utf-8"))
    assert cert["planning_status"] == "PASS"
    assert cert["execution_status"] == "PARTIAL"
    assert cert["status"] == "PASS_WITH_GAPS"
