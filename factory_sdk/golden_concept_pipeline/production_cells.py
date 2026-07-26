from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from .execution_models import ManufacturingContext, ProductionResult


class FoundationPassthroughCell:
    """Marks foundational dependencies as externally satisfied."""

    cell_name = "foundation_passthrough_cell"

    def run(self, context: ManufacturingContext) -> ProductionResult:
        out_dir = Path(context.working_directory) / "foundation_receipts"
        out_dir.mkdir(parents=True, exist_ok=True)

        path = out_dir / f"{context.task.asset_type}_{context.task.task_id}_receipt.json"

        payload = {
            "concept_id": context.concept_id,
            "task_id": context.task.task_id,
            "asset_type": context.task.asset_type,
            "status": "FOUNDATION_ASSUMED_AVAILABLE",
            "reason": context.task.reason,
            "source_distillation_ids": context.task.source_distillation_ids,
        }

        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return ProductionResult.pass_result(
            task=context.task,
            production_cell=self.cell_name,
            output_paths={"receipt": str(path)},
            message="Foundation dependency marked as available for GCMP execution.",
        )


class MentalModelTransformationCellAdapter:
    """GCMP adapter for the Health Mental Model Transformation Line."""

    cell_name = "mental_model_transformation_cell"
    SUPPORTED_CONCEPTS = {"copay", "waiting_period"}

    def run(self, context: ManufacturingContext) -> ProductionResult:
        if context.concept_id not in self.SUPPORTED_CONCEPTS:
            return ProductionResult.skipped(
                task=context.task,
                production_cell=self.cell_name,
                message=(
                    f"Concept '{context.concept_id}' is not yet supported by MMTC. "
                    f"Supported concepts: {', '.join(sorted(self.SUPPORTED_CONCEPTS))}. "
                    "No asset was manufactured."
                ),
            )

        report_path = context.primary_report_path()
        if not report_path:
            return ProductionResult.fail_result(
                task=context.task,
                production_cell=self.cell_name,
                message="No source distillation report path found for mental model manufacturing.",
            )

        path = Path(report_path)
        if not path.exists():
            return ProductionResult.fail_result(
                task=context.task,
                production_cell=self.cell_name,
                message=f"Source distillation report does not exist: {path}",
            )

        from knowledge_domains.health.mental_model_transformation.mental_model_transformation_line import (
            MentalModelTransformationLine,
        )

        report: Dict[str, object] = json.loads(path.read_text(encoding="utf-8"))

        line = MentalModelTransformationLine(
            output_root=Path(context.working_directory).parent / "mental_models"
        )

        result = line.manufacture_from_report(report)

        if not result:
            return ProductionResult.skipped(
                task=context.task,
                production_cell=self.cell_name,
                message="MMTC skipped report because incoming inspection failed.",
            )

        return ProductionResult.pass_result(
            task=context.task,
            production_cell=self.cell_name,
            output_paths={key: str(value) for key, value in result.items()},
            message="Mental Model Asset manufactured by MMTC.",
        )


class FinancialOutcomeSimulationCellAdapter:
    """GCMP adapter for the Health Financial Outcome Simulation Cell."""

    cell_name = "financial_outcome_simulation_cell"
    SUPPORTED_CONCEPTS = {"copay"}

    def run(self, context: ManufacturingContext) -> ProductionResult:
        if context.concept_id not in self.SUPPORTED_CONCEPTS:
            return ProductionResult.skipped(
                task=context.task,
                production_cell=self.cell_name,
                message=(
                    f"Concept '{context.concept_id}' is not yet supported by FOSC. "
                    f"Supported concepts: {', '.join(sorted(self.SUPPORTED_CONCEPTS))}. "
                    "No asset was manufactured."
                ),
            )

        from knowledge_domains.health.financial_outcome import (
            FinancialOutcomeSimulationCell,
        )

        cell = FinancialOutcomeSimulationCell(
            output_dir=(
                Path(context.working_directory).parent
                / "financial_outcomes"
                / context.concept_id
            )
        )

        outputs = cell.run(
            hospital_bill=500000,
            non_medical_expenses=50000,
            copay_percent=0.10,
        )

        return ProductionResult.pass_result(
            task=context.task,
            production_cell=self.cell_name,
            output_paths={key: str(value) for key, value in outputs.items()},
            message="Financial Outcome Asset manufactured by FOSC.",
        )