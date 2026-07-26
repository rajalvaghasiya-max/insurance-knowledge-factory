"""Generic topic-completeness capability.

MO-023I.1 defines contracts only. Evaluation and registry behaviour are added
in later bounded implementation units.
"""

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

__all__ = [
    "COMPLETENESS_STATUSES",
    "COMPONENT_STATUSES",
    "CONFLICT_POLICIES",
    "EXPLANATION_BLOCKING_STATUSES",
    "SUPPORTED_CONTRACT_VERSION",
    "UNRESOLVED_APPLICABILITY_POLICIES",
    "TopicCompletenessContractError",
    "TopicCompletenessResult",
    "TopicComponentDefinition",
    "TopicComponentResult",
    "TopicDefinition",
    "build_completeness_result",
    "build_component_definition",
    "build_component_result",
    "build_topic_definition",
]
