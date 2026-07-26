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

from insurance_intelligence.evaluation.disagreement import (
    EvaluationDisagreementError,
    analyze_evaluation_disagreement,
    analyze_evaluation_disagreements,
)

from insurance_intelligence.evaluation.responsibility import (
    ResponsibilityDecisionError,
    ResponsibilityEvidence,
    build_responsibility_decision,
    build_responsibility_decision_report,
)

from insurance_intelligence.evaluation.deepeval import (
    DeepEvalAdvisoryError,
    DeepEvalDependencyUnavailable,
    DeepEvalMetricConfig,
    DeepEvalMetricError,
    DeepEvalMetricRequest,
    DeepEvalMetricRunner,
    DeepEvalMetricTimeout,
    evaluate_deepeval_metric,
    evaluate_deepeval_metrics,
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
    "DeepEvalAdvisoryError",
    "DeepEvalDependencyUnavailable",
    "DeepEvalMetricConfig",
    "DeepEvalMetricError",
    "DeepEvalMetricRequest",
    "DeepEvalMetricRunner",
    "DeepEvalMetricTimeout",
    "DeterministicCheck",
    "DeterministicEvaluatorError",
    "DeterministicLLMEvaluator",
    "EvaluationBaselineReport",
    "EvaluationDataset",
    "EvaluationDatasetError",
    "EvaluationDisagreementError",
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
    "ResponsibilityDecisionError",
    "ResponsibilityEvidence",
    "ScenarioBaseline",
    "analyze_evaluation_disagreement",
    "analyze_evaluation_disagreements",
    "build_default_registry",
    "build_responsibility_decision",
    "build_responsibility_decision_report",
    "build_evaluation_input",
    "default_scenarios",
    "execute_controlled_case",
    "execute_controlled_cases",
    "evaluate_deepeval_metric",
    "evaluate_deepeval_metrics",
    "evaluate_hhem_advisory",
    "evaluate_hhem_batch",
    "load_evaluation_dataset",
]
