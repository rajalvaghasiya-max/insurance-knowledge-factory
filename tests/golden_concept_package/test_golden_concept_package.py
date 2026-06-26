import json
from pathlib import Path

from knowledge_factory.golden_concept_package.golden_concept_package_assembler import GoldenConceptPackageAssembler
from knowledge_factory.golden_concept_package.dependency_validator import DependencyValidator
from knowledge_factory.golden_concept_package.coverage_analyzer import CoverageAnalyzer


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_package_assembly_with_core_assets(tmp_path):
    write_json(tmp_path / "knowledge/factory/mental_models/copay/mma_1_mental_model_asset.json", {
        "asset_id": "mma_1", "concept_id": "copay", "certification_status": "PASS",
        "current_mental_model": {"belief": "bill -> copay"},
        "target_mental_model": {"belief": "admissible claim -> copay"},
        "transformation_plan": {"transformation_type": "Correction"},
    })
    write_json(tmp_path / "knowledge/factory/financial_outcomes/copay/foa_1_financial_outcome_asset.json", {
        "asset_id": "foa_1", "concept_id": "copay", "certification_status": "PASS",
        "financial_outcome": {"insurer_pays": 405000, "customer_pays": 95000, "financial_shock_level": "HIGH"},
    })
    outputs = GoldenConceptPackageAssembler(repo_root=tmp_path).run("copay")
    package = json.loads(Path(outputs["package"]).read_text())
    assert package["concept_id"] == "copay"
    assert package["package_certification"]["status"] == "PASS_WITH_GAPS"
    assert package["maturity_level"] == "SILVER"


def test_dependency_validator_fails_when_core_missing():
    result = DependencyValidator().validate({})
    assert result["status"] == "FAIL"
    assert "mental_model_asset" in result["core_missing_assets"]


def test_coverage_analyzer_complete(tmp_path):
    from knowledge_factory.golden_concept_package.package_models import AssetRecord
    inv = {k: AssetRecord(k, "FOUND") for k in DependencyValidator.REQUIRED}
    coverage = CoverageAnalyzer().analyze(inv)
    assert coverage.overall == "COMPLETE"


def test_package_assembly_complete_gold(tmp_path):
    for asset_type in DependencyValidator.REQUIRED:
        folder = {
            "knowledge_asset": "knowledge/factory/knowledge/copay",
            "understanding_asset": "knowledge/factory/understanding/copay",
            "mental_model_asset": "knowledge/factory/mental_models/copay",
            "financial_outcome_asset": "knowledge/factory/financial_outcomes/copay",
            "advisor_intelligence_asset": "knowledge/factory/advisor_intelligence/copay",
            "decision_intelligence_asset": "knowledge/factory/decision_intelligence/copay",
        }[asset_type]
        suffix = asset_type if asset_type not in ["mental_model_asset", "financial_outcome_asset"] else asset_type
        write_json(tmp_path / f"{folder}/x_{suffix}.json", {
            "asset_id": f"{asset_type}_1", "concept_id": "copay", "certification_status": "PASS",
            "target_mental_model": {"belief": "admissible claim -> copay"},
            "financial_outcome": {"customer_pays": 95000},
        })
    outputs = GoldenConceptPackageAssembler(repo_root=tmp_path).run("copay")
    package = json.loads(Path(outputs["package"]).read_text())
    assert package["coverage_analysis"]["overall"] == "COMPLETE"
    assert package["maturity_level"] == "GOLD"
