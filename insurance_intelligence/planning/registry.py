"""Governed plan-type, step, and template registry (MO-015).

Centralized and immutable at runtime, mirroring the Intent Analyzer's
rule-registry and the Context Builder's requirement-registry
convention. The planner (planner.py) consumes this registry rather
than embedding plan logic inline.
"""
from __future__ import annotations

from dataclasses import dataclass

from insurance_intelligence.contracts.reasoning_plan import (
    EXECUTION_MODES,
    EXPECTED_OUTCOME_TYPES,
    PLAN_TYPES,
    STAGE_OWNERS,
    STEP_TYPES,
)
from insurance_intelligence.intent.taxonomy import GOVERNED_INTENT_LABELS

# --- Plan type definitions ---------------------------------------------------

PLAN_TYPE_DEFINITIONS: dict[str, str] = {
    "DIRECT_FACT_PLAN": "Retrieve and state a specific governed fact directly.",
    "EXPLANATION_PLAN": "Explain a term, concept, or product in general or product-specific terms.",
    "CLAUSE_IMPACT_PLAN": "Explain what a specific clause or feature means in practice.",
    "DOCUMENT_INTERPRETATION_PLAN": "Interpret a specific passage of a specific document.",
    "COMPARISON_PLAN": "Compare two or more products, policies, or quotes on stated dimensions.",
    "SCENARIO_PLAN": "Work through a described claim or coverage scenario.",
    "CALCULATION_PLAN": "Perform a bounded numeric computation.",
    "SUITABILITY_PLAN": "Assess whether an option suits the user's stated situation.",
    "RECOMMENDATION_PLAN": "Form a conditional recommendation between options.",
    "ADVISOR_COMMUNICATION_PLAN": "Frame an explanation for an advisor's own client communication.",
}
assert set(PLAN_TYPE_DEFINITIONS) == PLAN_TYPES

# --- Step registry ------------------------------------------------------------


@dataclass(frozen=True)
class StepDefinition:
    step_type: str
    description: str
    stage_owner: str
    requires_evidence: bool
    requires_context: bool
    allowed_plan_types: frozenset[str]
    risk_level: str

    def __post_init__(self) -> None:
        if self.step_type not in STEP_TYPES:
            raise ValueError(f"{self.step_type} is not a governed step type")
        if self.stage_owner not in STAGE_OWNERS:
            raise ValueError(f"{self.step_type}: stage_owner {self.stage_owner!r} is not governed")
        if not self.allowed_plan_types <= PLAN_TYPES:
            raise ValueError(f"{self.step_type}: allowed_plan_types contains an ungoverned plan type")
        if self.risk_level not in {"low", "medium", "high"}:
            raise ValueError(f"{self.step_type}: risk_level {self.risk_level!r} is not governed")


_ALL_PLAN_TYPES = frozenset(PLAN_TYPES)

STEP_REGISTRY: dict[str, StepDefinition] = {
    d.step_type: d
    for d in (
        StepDefinition("VALIDATE_REQUEST_CONTEXT", "Confirm intent and context are internally consistent.", "PLANNING", False, True, _ALL_PLAN_TYPES, "low"),
        StepDefinition("RESOLVE_ENTITY_REFERENCES", "Resolve candidate entity mentions to governed identity.", "EVIDENCE_RESOLVER", True, True, _ALL_PLAN_TYPES, "medium"),
        StepDefinition("RESOLVE_DOCUMENT_REFERENCES", "Resolve a document reference to a governed document.", "EVIDENCE_RESOLVER", True, True, frozenset({"DIRECT_FACT_PLAN", "DOCUMENT_INTERPRETATION_PLAN"}), "medium"),
        StepDefinition("RESOLVE_POLICY_FACTS", "Resolve governed facts from a specific policy.", "EVIDENCE_RESOLVER", True, True, frozenset({"DIRECT_FACT_PLAN", "SCENARIO_PLAN", "RECOMMENDATION_PLAN"}), "medium"),
        StepDefinition("RESOLVE_PRODUCT_FACTS", "Resolve governed facts about a specific product.", "EVIDENCE_RESOLVER", True, True, frozenset({"EXPLANATION_PLAN", "COMPARISON_PLAN", "SUITABILITY_PLAN", "RECOMMENDATION_PLAN", "ADVISOR_COMMUNICATION_PLAN"}), "medium"),
        StepDefinition("RESOLVE_CLAUSE_EVIDENCE", "Resolve governed evidence for a specific clause or term.", "EVIDENCE_RESOLVER", True, True, frozenset({"EXPLANATION_PLAN", "CLAUSE_IMPACT_PLAN", "DOCUMENT_INTERPRETATION_PLAN"}), "medium"),
        StepDefinition("RESOLVE_COVERAGE_EVIDENCE", "Resolve governed evidence for a coverage question.", "EVIDENCE_RESOLVER", True, True, frozenset({"DIRECT_FACT_PLAN"}), "medium"),
        StepDefinition("RESOLVE_EXCLUSION_EVIDENCE", "Resolve governed evidence for an exclusion question.", "EVIDENCE_RESOLVER", True, True, frozenset({"DIRECT_FACT_PLAN"}), "medium"),
        StepDefinition("RESOLVE_CLAIM_CONDITIONS", "Resolve governed conditions relevant to a claim scenario.", "EVIDENCE_RESOLVER", True, True, frozenset({"SCENARIO_PLAN"}), "medium"),
        StepDefinition("RESOLVE_COMPARISON_DIMENSIONS", "Determine comparable dimensions across options.", "EVIDENCE_RESOLVER", True, True, frozenset({"COMPARISON_PLAN", "RECOMMENDATION_PLAN"}), "medium"),
        StepDefinition("RESOLVE_USER_OBJECTIVE", "Resolve the user's stated objective.", "EVIDENCE_RESOLVER", False, True, frozenset({"SUITABILITY_PLAN", "RECOMMENDATION_PLAN"}), "low"),
        StepDefinition("RESOLVE_SCENARIO_INPUTS", "Resolve the inputs needed for a calculation.", "EVIDENCE_RESOLVER", False, True, frozenset({"CALCULATION_PLAN"}), "low"),
        StepDefinition("VALIDATE_EVIDENCE_SUFFICIENCY", "Confirm resolved evidence is sufficient to proceed.", "REASONING_ENGINE", True, False, _ALL_PLAN_TYPES, "medium"),
        StepDefinition("DETECT_EVIDENCE_CONFLICTS", "Detect conflicts among resolved evidence.", "REASONING_ENGINE", True, False, frozenset({"DIRECT_FACT_PLAN", "SCENARIO_PLAN", "COMPARISON_PLAN", "RECOMMENDATION_PLAN"}), "medium"),
        StepDefinition("PERFORM_DETERMINISTIC_CALCULATION", "Perform a deterministic calculation.", "REASONING_ENGINE", True, False, frozenset({"SCENARIO_PLAN", "CALCULATION_PLAN", "RECOMMENDATION_PLAN"}), "medium"),
        StepDefinition("APPLY_DOMAIN_RULES", "Apply governed domain rules to resolved evidence.", "REASONING_ENGINE", True, False, frozenset({"CLAUSE_IMPACT_PLAN", "SCENARIO_PLAN", "SUITABILITY_PLAN", "RECOMMENDATION_PLAN"}), "medium"),
        StepDefinition("DERIVE_INSURANCE_IMPLICATIONS", "Derive an implication from evidence and rules.", "REASONING_ENGINE", True, False, frozenset({"EXPLANATION_PLAN", "CLAUSE_IMPACT_PLAN", "DOCUMENT_INTERPRETATION_PLAN", "ADVISOR_COMMUNICATION_PLAN", "SCENARIO_PLAN"}), "medium"),
        StepDefinition("COMPARE_OPTIONS", "Compare resolved facts across options.", "REASONING_ENGINE", True, False, frozenset({"COMPARISON_PLAN", "RECOMMENDATION_PLAN"}), "medium"),
        StepDefinition("ASSESS_SUITABILITY", "Assess suitability against the user's objective.", "REASONING_ENGINE", True, True, frozenset({"SUITABILITY_PLAN", "RECOMMENDATION_PLAN"}), "high"),
        StepDefinition("FORM_CONDITIONAL_RECOMMENDATION", "Form a conditional recommendation.", "REASONING_ENGINE", True, True, frozenset({"RECOMMENDATION_PLAN"}), "high"),
        StepDefinition("GENERATE_CONSUMER_EXPLANATION", "Draft a consumer-facing explanation.", "EXPLANATION_GENERATOR", False, False, _ALL_PLAN_TYPES, "low"),
        StepDefinition("GENERATE_ADVISOR_EXPLANATION", "Draft an advisor-facing explanation.", "EXPLANATION_GENERATOR", False, False, frozenset({"ADVISOR_COMMUNICATION_PLAN"}), "low"),
        StepDefinition("ASSEMBLE_EVIDENCE_TRACE", "Assemble the structured evidence/decision trace.", "RESPONSE_ASSEMBLER", False, False, _ALL_PLAN_TYPES, "low"),
        StepDefinition("APPLY_SAFETY_GATE", "Apply the governed safety gate before surfacing a result.", "SAFETY_GATE", False, False, _ALL_PLAN_TYPES, "high"),
    )
}
assert set(STEP_REGISTRY) == STEP_TYPES

RECOMMENDATION_REQUIRED_STEP = "FORM_CONDITIONAL_RECOMMENDATION"
SAFETY_GATE_STEP = "APPLY_SAFETY_GATE"
EVIDENCE_SUFFICIENCY_STEP = "VALIDATE_EVIDENCE_SUFFICIENCY"

# --- Intent-to-plan-type mapping ---------------------------------------------

INTENT_TO_PLAN_TYPE: dict[str, str] = {
    "TERM_EXPLANATION": "EXPLANATION_PLAN",
    "POLICY_FACT_LOOKUP": "DIRECT_FACT_PLAN",
    "POLICY_SUMMARY": "DOCUMENT_INTERPRETATION_PLAN",
    "COVERAGE_CHECK": "DIRECT_FACT_PLAN",
    "EXCLUSION_CHECK": "DIRECT_FACT_PLAN",
    "CLAIM_SCENARIO": "SCENARIO_PLAN",
    "CLAUSE_IMPLICATION": "CLAUSE_IMPACT_PLAN",
    "PRODUCT_EXPLANATION": "EXPLANATION_PLAN",
    "PRODUCT_COMPARISON": "COMPARISON_PLAN",
    "POLICY_COMPARISON": "COMPARISON_PLAN",
    "QUOTE_COMPARISON": "COMPARISON_PLAN",
    "SUITABILITY_ASSESSMENT": "SUITABILITY_PLAN",
    "RECOMMENDATION": "RECOMMENDATION_PLAN",
    "CALCULATION": "CALCULATION_PLAN",
    "DOCUMENT_INTERPRETATION": "DOCUMENT_INTERPRETATION_PLAN",
    "ADVISOR_EXPLANATION": "ADVISOR_COMMUNICATION_PLAN",
    # No natural plan-type target; used only when execution_mode is
    # NO_EXECUTION and no plan can meaningfully be formed.
    "CLARIFICATION_RESPONSE": "EXPLANATION_PLAN",
    "FOLLOW_UP": "EXPLANATION_PLAN",
    "OUT_OF_SCOPE": "EXPLANATION_PLAN",
}
assert set(INTENT_TO_PLAN_TYPE) == GOVERNED_INTENT_LABELS

PLAN_TYPE_TO_EXECUTION_MODE: dict[str, str] = {
    "DIRECT_FACT_PLAN": "DIRECT_GROUNDED",
    "EXPLANATION_PLAN": "INTERPRETIVE",
    "CLAUSE_IMPACT_PLAN": "INTERPRETIVE",
    "DOCUMENT_INTERPRETATION_PLAN": "INTERPRETIVE",
    "COMPARISON_PLAN": "DECISION_SUPPORT",
    "SCENARIO_PLAN": "INTERPRETIVE",
    "CALCULATION_PLAN": "INTERPRETIVE",
    "SUITABILITY_PLAN": "DECISION_SUPPORT",
    "RECOMMENDATION_PLAN": "DECISION_SUPPORT",
    "ADVISOR_COMMUNICATION_PLAN": "INTERPRETIVE",
}
assert set(PLAN_TYPE_TO_EXECUTION_MODE) == PLAN_TYPES
assert set(PLAN_TYPE_TO_EXECUTION_MODE.values()) <= EXECUTION_MODES

PLAN_TYPE_TO_EXPECTED_OUTCOME: dict[str, str] = {
    "DIRECT_FACT_PLAN": "DIRECT_FACT_RESPONSE",
    "EXPLANATION_PLAN": "GENERAL_EXPLANATION",
    "CLAUSE_IMPACT_PLAN": "CLAUSE_IMPACT_EXPLANATION",
    "DOCUMENT_INTERPRETATION_PLAN": "CLAUSE_IMPACT_EXPLANATION",
    "COMPARISON_PLAN": "COMPARISON_RESULT",
    "SCENARIO_PLAN": "SCENARIO_RESULT",
    "CALCULATION_PLAN": "CALCULATION_RESULT",
    "SUITABILITY_PLAN": "EDUCATIONAL_COMPARISON",
    "RECOMMENDATION_PLAN": "CONDITIONAL_RECOMMENDATION",
    "ADVISOR_COMMUNICATION_PLAN": "ADVISOR_EXPLANATION",
}
assert set(PLAN_TYPE_TO_EXPECTED_OUTCOME) == PLAN_TYPES
assert set(PLAN_TYPE_TO_EXPECTED_OUTCOME.values()) <= EXPECTED_OUTCOME_TYPES

# Product-specific explanation overrides the generic EXPLANATION_PLAN default
# when the intent is PRODUCT_EXPLANATION specifically (vs. TERM_EXPLANATION).
PRODUCT_EXPLANATION_OUTCOME = "PRODUCT_SPECIFIC_EXPLANATION"

# --- Plan templates (default step sequences per plan type) ------------------

# Each template lists step_types in execution order; the planner assigns
# step_id/sequence/dependencies mechanically from this order.
DEFAULT_STEPS_BY_PLAN_TYPE: dict[str, tuple[str, ...]] = {
    "DIRECT_FACT_PLAN": (
        "VALIDATE_REQUEST_CONTEXT",
        "RESOLVE_DOCUMENT_REFERENCES",
        "RESOLVE_POLICY_FACTS",
        "VALIDATE_EVIDENCE_SUFFICIENCY",
        "DETECT_EVIDENCE_CONFLICTS",
        "GENERATE_CONSUMER_EXPLANATION",
        "ASSEMBLE_EVIDENCE_TRACE",
        "APPLY_SAFETY_GATE",
    ),
    "EXPLANATION_PLAN": (
        "VALIDATE_REQUEST_CONTEXT",
        "RESOLVE_CLAUSE_EVIDENCE",
        "VALIDATE_EVIDENCE_SUFFICIENCY",
        "DERIVE_INSURANCE_IMPLICATIONS",
        "GENERATE_CONSUMER_EXPLANATION",
        "ASSEMBLE_EVIDENCE_TRACE",
        "APPLY_SAFETY_GATE",
    ),
    "CLAUSE_IMPACT_PLAN": (
        "VALIDATE_REQUEST_CONTEXT",
        "RESOLVE_CLAUSE_EVIDENCE",
        "VALIDATE_EVIDENCE_SUFFICIENCY",
        "APPLY_DOMAIN_RULES",
        "DERIVE_INSURANCE_IMPLICATIONS",
        "GENERATE_CONSUMER_EXPLANATION",
        "ASSEMBLE_EVIDENCE_TRACE",
        "APPLY_SAFETY_GATE",
    ),
    "DOCUMENT_INTERPRETATION_PLAN": (
        "VALIDATE_REQUEST_CONTEXT",
        "RESOLVE_DOCUMENT_REFERENCES",
        "RESOLVE_CLAUSE_EVIDENCE",
        "VALIDATE_EVIDENCE_SUFFICIENCY",
        "DERIVE_INSURANCE_IMPLICATIONS",
        "GENERATE_CONSUMER_EXPLANATION",
        "ASSEMBLE_EVIDENCE_TRACE",
        "APPLY_SAFETY_GATE",
    ),
    "COMPARISON_PLAN": (
        "VALIDATE_REQUEST_CONTEXT",
        "RESOLVE_ENTITY_REFERENCES",
        "RESOLVE_PRODUCT_FACTS",
        "RESOLVE_COMPARISON_DIMENSIONS",
        "VALIDATE_EVIDENCE_SUFFICIENCY",
        "DETECT_EVIDENCE_CONFLICTS",
        "COMPARE_OPTIONS",
        "GENERATE_CONSUMER_EXPLANATION",
        "ASSEMBLE_EVIDENCE_TRACE",
        "APPLY_SAFETY_GATE",
    ),
    "SCENARIO_PLAN": (
        "VALIDATE_REQUEST_CONTEXT",
        "RESOLVE_CLAIM_CONDITIONS",
        "VALIDATE_EVIDENCE_SUFFICIENCY",
        "PERFORM_DETERMINISTIC_CALCULATION",
        "APPLY_DOMAIN_RULES",
        "DERIVE_INSURANCE_IMPLICATIONS",
        "GENERATE_CONSUMER_EXPLANATION",
        "ASSEMBLE_EVIDENCE_TRACE",
        "APPLY_SAFETY_GATE",
    ),
    "CALCULATION_PLAN": (
        "VALIDATE_REQUEST_CONTEXT",
        "RESOLVE_SCENARIO_INPUTS",
        "PERFORM_DETERMINISTIC_CALCULATION",
        "GENERATE_CONSUMER_EXPLANATION",
        "ASSEMBLE_EVIDENCE_TRACE",
        "APPLY_SAFETY_GATE",
    ),
    "SUITABILITY_PLAN": (
        "VALIDATE_REQUEST_CONTEXT",
        "RESOLVE_USER_OBJECTIVE",
        "RESOLVE_ENTITY_REFERENCES",
        "RESOLVE_PRODUCT_FACTS",
        "VALIDATE_EVIDENCE_SUFFICIENCY",
        "APPLY_DOMAIN_RULES",
        "ASSESS_SUITABILITY",
        "GENERATE_CONSUMER_EXPLANATION",
        "ASSEMBLE_EVIDENCE_TRACE",
        "APPLY_SAFETY_GATE",
    ),
    "RECOMMENDATION_PLAN": (
        "VALIDATE_REQUEST_CONTEXT",
        "RESOLVE_USER_OBJECTIVE",
        "RESOLVE_ENTITY_REFERENCES",
        "RESOLVE_POLICY_FACTS",
        "RESOLVE_PRODUCT_FACTS",
        "RESOLVE_COMPARISON_DIMENSIONS",
        "VALIDATE_EVIDENCE_SUFFICIENCY",
        "DETECT_EVIDENCE_CONFLICTS",
        "PERFORM_DETERMINISTIC_CALCULATION",
        "APPLY_DOMAIN_RULES",
        "COMPARE_OPTIONS",
        "ASSESS_SUITABILITY",
        "FORM_CONDITIONAL_RECOMMENDATION",
        "APPLY_SAFETY_GATE",
        "GENERATE_CONSUMER_EXPLANATION",
        "ASSEMBLE_EVIDENCE_TRACE",
    ),
    "ADVISOR_COMMUNICATION_PLAN": (
        "VALIDATE_REQUEST_CONTEXT",
        "RESOLVE_ENTITY_REFERENCES",
        "RESOLVE_PRODUCT_FACTS",
        "VALIDATE_EVIDENCE_SUFFICIENCY",
        "DERIVE_INSURANCE_IMPLICATIONS",
        "GENERATE_ADVISOR_EXPLANATION",
        "ASSEMBLE_EVIDENCE_TRACE",
        "APPLY_SAFETY_GATE",
    ),
}
assert set(DEFAULT_STEPS_BY_PLAN_TYPE) == PLAN_TYPES

# --- Domain capability mapping (Health only implemented) --------------------

INTENT_TO_CAPABILITY: dict[str, str] = {
    "TERM_EXPLANATION": "HEALTH_TERM_EXPLANATION",
    "POLICY_FACT_LOOKUP": "HEALTH_POLICY_FACT_LOOKUP",
    "COVERAGE_CHECK": "HEALTH_COVERAGE_ANALYSIS",
    "EXCLUSION_CHECK": "HEALTH_EXCLUSION_ANALYSIS",
    "CLAUSE_IMPLICATION": "HEALTH_CLAUSE_IMPLICATION",
    "CLAIM_SCENARIO": "HEALTH_CLAIM_SCENARIO",
    "PRODUCT_EXPLANATION": "HEALTH_PRODUCT_EXPLANATION",
    "PRODUCT_COMPARISON": "HEALTH_PRODUCT_COMPARISON",
    "QUOTE_COMPARISON": "HEALTH_QUOTE_COMPARISON",
    "SUITABILITY_ASSESSMENT": "HEALTH_SUITABILITY_ASSESSMENT",
    "ADVISOR_EXPLANATION": "HEALTH_ADVISOR_EXPLANATION",
}
