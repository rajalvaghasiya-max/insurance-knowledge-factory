"""Generic topic-completeness capability."""

from insurance_intelligence.contracts.topic_completeness import (
    COMPLETENESS_STATUSES,
    COMPONENT_STATUSES,
    CONFLICT_POLICIES,
    EXPLANATION_BLOCKING_STATUSES,
    SUPPORTED_CONTRACT_VERSION,
    UNRESOLVED_APPLICABILITY_POLICIES,
    TopicCompletenessContractError,
    TopicCompletenessResult,
    TopicComponentDefinition,
    TopicComponentResult,
    TopicDefinition,
    build_completeness_result,
    build_component_definition,
    build_component_result,
    build_topic_definition,
)
from insurance_intelligence.topic_completeness.catalogue import (
    CATALOGUE_VERSION,
    build_conditional_obligation_definition,
    build_coverage_limit_definition,
    build_default_topic_registry,
    build_eligibility_and_consequence_definition,
    build_waiting_period_definition,
    default_topic_definitions,
)
from insurance_intelligence.topic_completeness.evaluator import (
    TopicCompletenessEvaluationError,
    evaluate_topic_completeness,
)
from insurance_intelligence.topic_completeness.registry import (
    TopicCompletenessRegistry,
    TopicCompletenessRegistryError,
)

__all__ = [
    "CATALOGUE_VERSION",
    "COMPLETENESS_STATUSES",
    "COMPONENT_STATUSES",
    "CONFLICT_POLICIES",
    "EXPLANATION_BLOCKING_STATUSES",
    "SUPPORTED_CONTRACT_VERSION",
    "UNRESOLVED_APPLICABILITY_POLICIES",
    "TopicCompletenessContractError",
    "TopicCompletenessEvaluationError",
    "TopicCompletenessRegistry",
    "TopicCompletenessRegistryError",
    "TopicCompletenessResult",
    "TopicComponentDefinition",
    "TopicComponentResult",
    "TopicDefinition",
    "build_completeness_result",
    "build_component_definition",
    "build_component_result",
    "build_conditional_obligation_definition",
    "build_coverage_limit_definition",
    "build_default_topic_registry",
    "build_eligibility_and_consequence_definition",
    "build_topic_definition",
    "build_waiting_period_definition",
    "default_topic_definitions",
    "evaluate_topic_completeness",
]
