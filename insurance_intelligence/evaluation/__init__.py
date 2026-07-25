"""End-to-end Intelligence Layer evaluation contracts, scenarios, and service."""

from insurance_intelligence.evaluation.dataset import (
    EvaluationDataset,
    EvaluationDatasetError,
    load_evaluation_dataset,
)
from insurance_intelligence.evaluation.scenarios import (
    EvaluationScenarioRegistry,
    EvaluationScenarioRegistryError,
    build_default_registry,
    default_scenarios,
)
from insurance_intelligence.evaluation.service import (
    EvaluationBaselineReport,
    EvaluationService,
    EvaluationServiceError,
    ScenarioBaseline,
)

__all__ = [
    "EvaluationBaselineReport",
    "EvaluationDataset",
    "EvaluationDatasetError",
    "EvaluationScenarioRegistry",
    "EvaluationScenarioRegistryError",
    "EvaluationService",
    "EvaluationServiceError",
    "ScenarioBaseline",
    "build_default_registry",
    "default_scenarios",
    "load_evaluation_dataset",
]
