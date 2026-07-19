"""Governed, centralized required-context registry (MO-014).

Maps each governed intent to the context keys it requires or may
optionally use. Deliberately centralized (a single registry, not
scattered per-intent conditionals) so requirements are auditable and
extensible only through code change and review, mirroring the
Intent Analyzer's rule-registry convention.
"""
from __future__ import annotations

from dataclasses import dataclass

from insurance_intelligence.contracts.context import CONTEXT_CATEGORIES, MATERIALITY_VALUES
from insurance_intelligence.intent.taxonomy import GOVERNED_INTENT_LABELS


@dataclass(frozen=True)
class ContextRequirement:
    requirement_id: str
    intent: str
    context_key: str
    category: str
    required: bool
    materiality: str
    clarification_question: str

    def __post_init__(self) -> None:
        if self.intent not in GOVERNED_INTENT_LABELS:
            raise ValueError(f"{self.requirement_id}: intent {self.intent!r} is not governed")
        if self.category not in CONTEXT_CATEGORIES:
            raise ValueError(f"{self.requirement_id}: category {self.category!r} is not governed")
        if self.materiality not in MATERIALITY_VALUES:
            raise ValueError(f"{self.requirement_id}: materiality {self.materiality!r} is not governed")


REQUIREMENT_REGISTRY: tuple[ContextRequirement, ...] = (
    # TERM_EXPLANATION
    ContextRequirement(
        "term_explanation_term", "TERM_EXPLANATION", "term_or_concept", "DOMAIN", True, "high",
        "Which term or concept would you like explained?",
    ),
    ContextRequirement(
        "term_explanation_policy_ref", "TERM_EXPLANATION", "policy_reference", "POLICY", False, "low",
        "Is this about a specific policy, or a general explanation?",
    ),
    ContextRequirement(
        "term_explanation_product_ref", "TERM_EXPLANATION", "product_reference", "PRODUCT", False, "low",
        "Is this about a specific product?",
    ),
    # POLICY_FACT_LOOKUP
    ContextRequirement(
        "policy_fact_lookup_ref", "POLICY_FACT_LOOKUP", "policy_or_document_reference", "POLICY", True, "high",
        "Which policy or document should I check this fact against?",
    ),
    ContextRequirement(
        "policy_fact_lookup_fact", "POLICY_FACT_LOOKUP", "requested_fact", "SCENARIO", True, "high",
        "What specific fact would you like me to look up?",
    ),
    # POLICY_SUMMARY
    ContextRequirement(
        "policy_summary_ref", "POLICY_SUMMARY", "policy_or_document_reference", "POLICY", True, "high",
        "Which policy would you like summarized?",
    ),
    # COVERAGE_CHECK
    ContextRequirement(
        "coverage_check_subject", "COVERAGE_CHECK", "coverage_subject", "SCENARIO", True, "high",
        "What would you like me to check coverage for?",
    ),
    ContextRequirement(
        "coverage_check_ref", "COVERAGE_CHECK", "policy_or_product_reference", "POLICY", True, "high",
        "Which policy or product would you like me to check for this coverage?",
    ),
    # EXCLUSION_CHECK
    ContextRequirement(
        "exclusion_check_subject", "EXCLUSION_CHECK", "exclusion_subject", "SCENARIO", True, "high",
        "What would you like me to check for exclusion?",
    ),
    ContextRequirement(
        "exclusion_check_ref", "EXCLUSION_CHECK", "policy_or_product_reference", "POLICY", True, "high",
        "Which policy or product would you like me to check?",
    ),
    # CLAIM_SCENARIO
    ContextRequirement(
        "claim_scenario_desc", "CLAIM_SCENARIO", "claim_scenario", "SCENARIO", True, "high",
        "Could you describe the claim scenario in more detail?",
    ),
    ContextRequirement(
        "claim_scenario_ref", "CLAIM_SCENARIO", "policy_or_product_reference", "POLICY", True, "high",
        "Which policy or product does this claim relate to?",
    ),
    ContextRequirement(
        "claim_scenario_amount", "CLAIM_SCENARIO", "claim_amount", "FINANCIAL", False, "medium",
        "What is the claim amount?",
    ),
    ContextRequirement(
        "claim_scenario_admissible", "CLAIM_SCENARIO", "admissible_amount", "FINANCIAL", False, "low",
        "Do you know the admissible claim amount?",
    ),
    ContextRequirement(
        "claim_scenario_deductible", "CLAIM_SCENARIO", "deductible", "FINANCIAL", False, "low",
        "Does your policy have a deductible?",
    ),
    ContextRequirement(
        "claim_scenario_copay", "CLAIM_SCENARIO", "copay", "FINANCIAL", False, "low",
        "Does your policy have a co-payment clause?",
    ),
    ContextRequirement(
        "claim_scenario_hosp_date", "CLAIM_SCENARIO", "hospitalization_date", "TEMPORAL", False, "low",
        "When did (or will) the hospitalization occur?",
    ),
    # CLAUSE_IMPLICATION
    ContextRequirement(
        "clause_implication_clause", "CLAUSE_IMPLICATION", "clause_or_feature", "SCENARIO", True, "high",
        "Which clause or feature would you like explained?",
    ),
    ContextRequirement(
        "clause_implication_ref", "CLAUSE_IMPLICATION", "policy_or_product_reference", "POLICY", False, "medium",
        "Is this about a specific policy or product?",
    ),
    ContextRequirement(
        "clause_implication_scenario", "CLAUSE_IMPLICATION", "scenario_context", "SCENARIO", False, "low",
        "Is there a specific scenario you'd like me to apply this to?",
    ),
    # PRODUCT_EXPLANATION
    ContextRequirement(
        "product_explanation_ref", "PRODUCT_EXPLANATION", "product_reference", "PRODUCT", True, "high",
        "Which product would you like me to explain?",
    ),
    # PRODUCT_COMPARISON
    ContextRequirement(
        "product_comparison_1", "PRODUCT_COMPARISON", "comparison_subject_1", "PRODUCT", True, "high",
        "Which first product would you like to compare?",
    ),
    ContextRequirement(
        "product_comparison_2", "PRODUCT_COMPARISON", "comparison_subject_2", "PRODUCT", True, "high",
        "Which second product would you like to compare?",
    ),
    ContextRequirement(
        "product_comparison_objective", "PRODUCT_COMPARISON", "comparison_objective", "SCENARIO", False, "low",
        "What matters most to you in this comparison?",
    ),
    ContextRequirement(
        "product_comparison_priority", "PRODUCT_COMPARISON", "user_priority", "SCENARIO", False, "low",
        "Do you have a priority (e.g. price, coverage breadth) for this comparison?",
    ),
    # POLICY_COMPARISON
    ContextRequirement(
        "policy_comparison_1", "POLICY_COMPARISON", "comparison_subject_1", "POLICY", True, "high",
        "Which first policy would you like to compare?",
    ),
    ContextRequirement(
        "policy_comparison_2", "POLICY_COMPARISON", "comparison_subject_2", "POLICY", True, "high",
        "Which second policy would you like to compare?",
    ),
    # QUOTE_COMPARISON
    ContextRequirement(
        "quote_comparison_1", "QUOTE_COMPARISON", "quote_reference_1", "PRODUCT", True, "high",
        "Could you share the first quote you'd like compared?",
    ),
    ContextRequirement(
        "quote_comparison_2", "QUOTE_COMPARISON", "quote_reference_2", "PRODUCT", True, "high",
        "Could you share the second quote you'd like compared?",
    ),
    ContextRequirement(
        "quote_comparison_objective", "QUOTE_COMPARISON", "comparison_objective", "SCENARIO", False, "low",
        "What matters most to you in comparing these quotes?",
    ),
    # SUITABILITY_ASSESSMENT
    ContextRequirement(
        "suitability_subject", "SUITABILITY_ASSESSMENT", "subject_reference", "PRODUCT", True, "high",
        "Which product or option would you like assessed?",
    ),
    ContextRequirement(
        "suitability_objective", "SUITABILITY_ASSESSMENT", "user_objective", "SCENARIO", True, "high",
        "What are you hoping this option will help with?",
    ),
    ContextRequirement(
        "suitability_age", "SUITABILITY_ASSESSMENT", "age", "USER", True, "medium",
        "What is your age?",
    ),
    ContextRequirement(
        "suitability_family", "SUITABILITY_ASSESSMENT", "family_composition", "USER", True, "medium",
        "Who would this cover -- just you, or your family too?",
    ),
    ContextRequirement(
        "suitability_existing_coverage", "SUITABILITY_ASSESSMENT", "existing_coverage", "POLICY", True, "medium",
        "What coverage do you currently have?",
    ),
    ContextRequirement(
        "suitability_budget", "SUITABILITY_ASSESSMENT", "budget", "FINANCIAL", True, "medium",
        "Do you have a budget in mind?",
    ),
    # RECOMMENDATION
    ContextRequirement(
        "recommendation_options", "RECOMMENDATION", "decision_options", "SCENARIO", True, "high",
        "What options are you deciding between?",
    ),
    ContextRequirement(
        "recommendation_objective", "RECOMMENDATION", "user_objective", "SCENARIO", True, "high",
        "What's most important to you in this decision?",
    ),
    ContextRequirement(
        "recommendation_existing_coverage", "RECOMMENDATION", "existing_coverage", "POLICY", True, "medium",
        "What coverage do you currently have?",
    ),
    ContextRequirement(
        "recommendation_age", "RECOMMENDATION", "age", "USER", True, "medium",
        "What is your age?",
    ),
    ContextRequirement(
        "recommendation_family", "RECOMMENDATION", "family_composition", "USER", True, "medium",
        "Who would this cover -- just you, or your family too?",
    ),
    ContextRequirement(
        "recommendation_budget", "RECOMMENDATION", "budget", "FINANCIAL", True, "medium",
        "Do you have a budget in mind?",
    ),
    ContextRequirement(
        "recommendation_risk_priority", "RECOMMENDATION", "risk_priority", "SCENARIO", True, "medium",
        "How would you prioritize lower premium versus broader coverage?",
    ),
    # CALCULATION
    ContextRequirement(
        "calculation_inputs", "CALCULATION", "calculation_inputs", "FINANCIAL", True, "high",
        "What figures should I use for this calculation?",
    ),
    ContextRequirement(
        "calculation_goal", "CALCULATION", "calculation_goal", "SCENARIO", True, "high",
        "What would you like calculated?",
    ),
    # DOCUMENT_INTERPRETATION
    ContextRequirement(
        "document_interpretation_ref", "DOCUMENT_INTERPRETATION", "document_reference", "DOCUMENT", True, "high",
        "Which document would you like me to interpret?",
    ),
    ContextRequirement(
        "document_interpretation_subject", "DOCUMENT_INTERPRETATION", "document_subject", "SCENARIO", True, "high",
        "Which part of the document would you like explained?",
    ),
    # ADVISOR_EXPLANATION
    ContextRequirement(
        "advisor_explanation_subject", "ADVISOR_EXPLANATION", "subject_reference", "PRODUCT", True, "high",
        "Which product or topic would you like framed for your client?",
    ),
    ContextRequirement(
        "advisor_explanation_profile", "ADVISOR_EXPLANATION", "customer_profile", "USER", False, "low",
        "Would it help to know a bit about your client's profile?",
    ),
    ContextRequirement(
        "advisor_explanation_goal", "ADVISOR_EXPLANATION", "advisor_goal", "SCENARIO", False, "low",
        "What's the goal of this conversation with your client?",
    ),
    # FOLLOW_UP
    ContextRequirement(
        "follow_up_reference", "FOLLOW_UP", "resolved_follow_up_reference", "CONVERSATION", True, "high",
        "Could you clarify what you're referring to?",
    ),
    # CLARIFICATION_RESPONSE
    ContextRequirement(
        "clarification_response_target", "CLARIFICATION_RESPONSE", "clarification_target", "CONVERSATION", True, "high",
        "Could you clarify which question you're answering?",
    ),
    ContextRequirement(
        "clarification_response_value", "CLARIFICATION_RESPONSE", "response_value", "CONVERSATION", True, "high",
        "Could you provide the answer to the earlier question?",
    ),
)


def requirements_for_intent(intent: str) -> tuple[ContextRequirement, ...]:
    return tuple(requirement for requirement in REQUIREMENT_REGISTRY if requirement.intent == intent)
