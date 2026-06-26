from knowledge_factory.gmvs.gmvs_report_builder import GMVSReportBuilder


def test_first_concept_is_a_baseline_run(tmp_path):
    builder = GMVSReportBuilder(tmp_path)

    scope = builder.determine_validation_scope("copay")

    assert scope == "BASELINE"


def test_second_concept_is_a_cross_concept_run(tmp_path):
    copay_report_dir = (
        tmp_path
        / "knowledge"
        / "factory"
        / "gmvs"
        / "copay"
    )
    copay_report_dir.mkdir(parents=True)

    (copay_report_dir / "gmvs_report.json").write_text(
        "{}",
        encoding="utf-8",
    )

    builder = GMVSReportBuilder(tmp_path)

    scope = builder.determine_validation_scope("waiting_period")

    assert scope == "CROSS_CONCEPT"