from pathlib import Path

from knowledge_factory.gmvs.gmvs_report_builder import GMVSReportBuilder


def test_gmvs_report_builder_creates_report_for_copay():
    report = GMVSReportBuilder(Path.cwd()).build("copay", "Copay")

    assert report.concept_id == "copay"
    assert report.concept_name == "Copay"
    assert report.factory_version == "1.0"

    assert report.architecture_validation.name == "architecture"
    assert report.readiness_validation.name == "readiness"
    assert report.manufacturing_validation.name == "manufacturing"
    assert report.reuse_analysis.name == "reuse"
    assert report.governance_validation.name == "governance"

    assert report.scorecard.factory_stability_score >= 0
    assert report.certification_status in {"PASS", "PASS_WITH_GAPS", "FAIL"}
    assert report.recommendations