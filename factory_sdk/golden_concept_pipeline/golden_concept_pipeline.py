from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from .certification import GoldenConceptCertifier
from .department_dispatcher import DepartmentDispatcher
from .dependency_resolver import DependencyResolver
from .manufacturing_queue import ManufacturingQueueBuilder
from .package_assembler import PackageAssembler
from .execution_dispatcher import ExecutionDispatcher
from .manufacturing_state import ManufacturingStateManager
from .output_collector import OutputCollector
from .production_cell_registry import ProductionCellRegistry
from .production_cells import FoundationPassthroughCell, MentalModelTransformationCellAdapter, FinancialOutcomeSimulationCellAdapter
from .pipeline_models import (
    DependencyGraph,
    DispatchPlan,
    GoldenConceptCertification,
    GoldenConceptPackage,
    ManufacturingQueue,
    SourceDistillationReport,
)
from .report_reader import DistillationReportReader


class GoldenConceptManufacturingPipeline:
    """GCMP v1.0: converts KDE distillation reports into a Golden Concept manufacturing package."""

    def __init__(self) -> None:
        self.reader = DistillationReportReader()
        self.queue_builder = ManufacturingQueueBuilder()
        self.dependency_resolver = DependencyResolver()
        self.dispatcher = DepartmentDispatcher()
        self.assembler = PackageAssembler()
        self.certifier = GoldenConceptCertifier()
        self.registry = ProductionCellRegistry()
        self._register_default_cells()
        self.execution_dispatcher = ExecutionDispatcher(self.registry)
        self.state_manager = ManufacturingStateManager()
        self.output_collector = OutputCollector()

    def _register_default_cells(self) -> None:
        foundation = FoundationPassthroughCell()
        self.registry.register("knowledge_asset", foundation, version="1.0")
        self.registry.register("understanding_gap", foundation, version="1.0")
        self.registry.register("mental_model_asset", MentalModelTransformationCellAdapter(), version="1.0")
        self.registry.register("financial_simulation", FinancialOutcomeSimulationCellAdapter(), version="1.0")

    def run_from_dir(self, *, distillation_dir: str | Path, concept_id: str, output_dir: str | Path) -> Dict[str, Path]:
        reports = self.reader.read_dir(distillation_dir, concept_id=concept_id)
        return self.run(reports=reports, concept_id=concept_id, output_dir=output_dir)

    def run(self, *, reports: List[SourceDistillationReport], concept_id: str, output_dir: str | Path) -> Dict[str, Path]:
        if not reports:
            raise ValueError(f"No distillation reports supplied for concept_id={concept_id!r}")

        raw_queue = self.queue_builder.build(reports, concept_id)
        queue, graph = self.dependency_resolver.resolve(raw_queue)
        dispatch = self.dispatcher.dispatch(queue)
        execution_log = self.execution_dispatcher.execute(
            queue=queue,
            reports=reports,
            working_directory=output_dir,
            distillation_reports_dir=Path(reports[0].source_path).parent if reports[0].source_path else "knowledge/factory/distillation/reports",
        )
        state = self.state_manager.build_state(queue=queue, dispatch=dispatch, results=execution_log.results)
        package = self.assembler.assemble(concept_id, reports, queue)
        certification = self.certifier.certify(
            concept_id=concept_id,
            queue=queue,
            graph=graph,
            dispatch=dispatch,
            package=package,
            state=state,
        )
        return self.write_outputs(output_dir, queue, graph, dispatch, package, certification, execution_log, state)

    def write_outputs(
        self,
        output_dir: str | Path,
        queue: ManufacturingQueue,
        graph: DependencyGraph,
        dispatch: DispatchPlan,
        package: GoldenConceptPackage,
        certification: GoldenConceptCertification,
        execution_log,
        state,
    ) -> Dict[str, Path]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        outputs = {
            "manufacturing_queue": out / "manufacturing_queue.json",
            "dependency_graph": out / "dependency_graph.json",
            "dispatch_plan": out / "dispatch_plan.json",
            "golden_concept_package": out / "golden_concept_package.json",
            "certification": out / "certification.json",
            "execution_log": out / "execution_log.json",
            "manufacturing_state": out / "manufacturing_state.json",
            "production_cell_registry": out / "production_cell_registry.json",
        }
        payloads = {
            "manufacturing_queue": queue.to_dict(),
            "dependency_graph": graph.to_dict(),
            "dispatch_plan": dispatch.to_dict(),
            "golden_concept_package": package.to_dict(),
            "certification": certification.to_dict(),
            "execution_log": execution_log.to_dict(),
            "manufacturing_state": state.to_dict(),
            "production_cell_registry": self.registry.to_dict(),
        }
        for key, path in outputs.items():
            path.write_text(json.dumps(payloads[key], indent=2, ensure_ascii=False), encoding="utf-8")
        return outputs
