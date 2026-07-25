"""End-to-end Intelligence Layer evaluation contracts, scenarios, and service."""

from insurance_intelligence.evaluation.deterministic import (
    DeterministicCheck,
    DeterministicEvaluatorError,
    DeterministicLLMEvaluator,
)
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

from insurance_intelligence.evaluation.harness import (
    ControlledHarnessConfig,
    ControlledHarnessError,
    build_evaluation_input,
    execute_controlled_case,
    execute_controlled_cases,
)
from insurance_intelligence.evaluation.provider import (
    ControlledEvaluationProvider,
    ControlledProviderError,
    ControlledProviderExecutionError,
    ControlledProviderTimeout,
    ProviderRequest,
    ProviderResponse,
)

from insurance_intelligence.evaluation.hhem import (
    HHEMAdvisoryConfig,
    HHEMAdvisoryError,
    HHEMInferenceError,
    HHEMInferenceTimeout,
    HHEMModelUnavailable,
    HHEMScoreRequest,
    HHEMScorer,
    evaluate_hhem_advisory,
    evaluate_hhem_batch,
)

__all__ = [
    "ControlledEvaluationProvider",
    "ControlledHarnessConfig",
    "ControlledHarnessError",
    "ControlledProviderError",
    "ControlledProviderExecutionError",
    "ControlledProviderTimeout",
    "DeterministicCheck",
    "DeterministicEvaluatorError",
    "DeterministicLLMEvaluator",
    "EvaluationBaselineReport",
    "EvaluationDataset",
    "EvaluationDatasetError",
    "EvaluationScenarioRegistry",
    "EvaluationScenarioRegistryError",
    "EvaluationService",
    "EvaluationServiceError",
    "HHEMAdvisoryConfig",
    "HHEMAdvisoryError",
    "HHEMInferenceError",
    "HHEMInferenceTimeout",
    "HHEMModelUnavailable",
    "HHEMScoreRequest",
    "HHEMScorer",
    "ProviderRequest",
    "ProviderResponse",
    "ScenarioBaseline",
    "build_default_registry",
    "build_evaluation_input",
    "default_scenarios",
    "execute_controlled_case",
    "execute_controlled_cases",
    "evaluate_hhem_advisory",
    "evaluate_hhem_batch",
    "load_evaluation_dataset",
]
