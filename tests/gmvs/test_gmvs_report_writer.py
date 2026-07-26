from pathlib import Path

from knowledge_factory.gmvs.gmvs_report_builder import GMVSReportBuilder
from knowledge_factory.gmvs.gmvs_report_writer import GMVSReportWriter


def test_gmvs_report_writer_creates_json_and_summary(tmp_path):
    report = GMVSReportBuilder(Path.cwd()).build("copay", "Copay")

    writer = GMVSReportWriter(tmp_path)
    json_path, summary_path = writer.write(report)

    assert json_path.exists()
    assert summary_path.exists()

    assert json_path.name == "gmvs_report.json"
    assert summary_path.name == "gmvs_summary.txt"

    assert '"concept_id": "copay"' in json_path.read_text(encoding="utf-8")
    assert "GMVS" in summary_path.read_text(encoding="utf-8")