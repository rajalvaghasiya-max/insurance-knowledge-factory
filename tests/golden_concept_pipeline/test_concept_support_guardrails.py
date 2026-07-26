from factory_sdk.golden_concept_pipeline.execution_models import ManufacturingContext
from factory_sdk.golden_concept_pipeline.pipeline_models import ManufacturingTask
from factory_sdk.golden_concept_pipeline.production_cells import (
    FinancialOutcomeSimulationCellAdapter,
    MentalModelTransformationCellAdapter,
)


def build_context(
    tmp_path,
    asset_type: str,
    concept_id: str = "waiting_period",
) -> ManufacturingContext:
    task = ManufacturingTask.create(
        concept_id=concept_id,
        asset_type=asset_type,
        target_department="test",
        priority="high",
        reason="Guardrail test",
        source_distillation_ids=[],
        source_observation_ids=[],
    )

    return ManufacturingContext(
        concept_id=concept_id,
        task=task,
        working_directory=str(tmp_path),
        distillation_reports_dir=str(tmp_path),
        report_paths_by_id={},
    )


def test_mmtc_skips_unsupported_concept_without_writing_asset(tmp_path):
    result = MentalModelTransformationCellAdapter().run(
        build_context(
            tmp_path,
            "mental_model_asset",
            concept_id="room_rent_limit",
        )
    )

    assert result.status == "SKIPPED"
    assert result.output_paths == {}
    assert "not yet supported by MMTC" in result.message


def test_fosc_skips_unsupported_concept_without_writing_asset(tmp_path):
    result = FinancialOutcomeSimulationCellAdapter().run(
        build_context(tmp_path, "financial_simulation")
    )

    assert result.status == "SKIPPED"
    assert result.output_paths == {}
    assert "not yet supported by FOSC" in result.message