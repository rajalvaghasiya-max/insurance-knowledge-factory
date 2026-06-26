from knowledge_factory.gmvs.gmvs_models import (
    GMVSReport,
    GMVSScorecard,
    GMVSValidationResult,
)


def test_gmvs_models_can_be_created():
    architecture = GMVSValidationResult(
        name="architecture",
        status="PASS",
        score=100,
        notes=["No architecture changes required."],
    )

    readiness = GMVSValidationResult(
        name="readiness",
        status="PASS",
        score=100,
        notes=["Concept is ready for manufacturing validation."],
    )

    manufacturing = GMVSValidationResult(
        name="manufacturing",
        status="PASS",
        score=100,
        notes=["Golden package complete."],
    )

    reuse = GMVSValidationResult(
        name="reuse",
        status="PASS",
        score=98,
        notes=["High code reuse."],
    )

    governance = GMVSValidationResult(
        name="governance",
        status="PASS",
        score=100,
        notes=["FER available."],
    )

    scorecard = GMVSScorecard(
        concept_id="copay",
        concept_name="Copay",
        architecture_reuse_percent=100,
        department_reuse_percent=100,
        infrastructure_reuse_percent=100,
        architecture_changes_required=0,
        new_infrastructure_files=0,
        concept_specific_code_files=0,
        fer_entries_generated=0,
        factory_stability_score=100,
        factory_maturity="GOLD",
        manufacturing_status="Manufactured without architecture changes",
        overall_rating="★★★★★",
    )

    report = GMVSReport(
        report_id="gmvs_test",
        concept_id="copay",
        concept_name="Copay",
        version="1.0",
        factory_version="1.0",
        architecture_validation=architecture,
        readiness_validation=readiness,
        manufacturing_validation=manufacturing,
        reuse_analysis=reuse,
        governance_validation=governance,
        scorecard=scorecard,
        recommendations=["Proceed to next concept."],
        certification_status="PASS",
        created_at="2026-06-26T00:00:00+00:00",
        validation_scope="BASELINE",
    )

    assert report.concept_id == "copay"
    assert report.factory_version == "1.0"
    assert report.readiness_validation.status == "PASS"
    assert report.scorecard.factory_stability_score == 100
    assert report.scorecard.factory_maturity == "GOLD"
    assert report.certification_status == "PASS"
    assert report.validation_scope == "BASELINE"