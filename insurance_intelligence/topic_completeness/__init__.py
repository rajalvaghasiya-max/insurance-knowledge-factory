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
from insurance_intelligence.topic_completeness.registry import (
    TopicCompletenessRegistry,
    TopicCompletenessRegistryError,
)

__all__ = [
    "COMPLETENESS_STATUSES",
    "COMPONENT_STATUSES",
    "CONFLICT_POLICIES",
    "EXPLANATION_BLOCKING_STATUSES",
    "SUPPORTED_CONTRACT_VERSION",
    "UNRESOLVED_APPLICABILITY_POLICIES",
    "TopicCompletenessContractError",
    "TopicCompletenessRegistry",
    "TopicCompletenessRegistryError",
    "TopicCompletenessResult",
    "TopicComponentDefinition",
    "TopicComponentResult",
    "TopicDefinition",
    "build_completeness_result",
    "build_component_definition",
    "build_component_result",
    "build_topic_definition",
]
