"""Versioned, executable contracts for the Reasoning Planner (MO-015).

Same repository convention as intent.py / context.py: frozen
dataclasses constructed only through validating factory functions.
No new dependency.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from insurance_intelligence.contracts.context import ContextBuilderOutput
from insurance_intelligence.contracts.intent import IntentAnalyzerOutput

SUPPORTED_CONTRACT_VERSION = "1.0"

DOMAIN_VALUES = frozenset({"health", "motor", "life", "claims", "unknown"})
PLANNING_MODE_VALUES = frozenset({"AUTO", "DIRECT", "INTERPRETIVE", "DECISION_SUPPORT"})

PLAN_TYPES = frozenset(
    {
        "DIRECT_FACT_PLAN",
        "EXPLANATION_PLAN",
        "CLAUSE_IMPACT_PLAN",
        "DOCUMENT_INTERPRETATION_PLAN",
        "COMPARISON_PLAN",
        "SCENARIO_PLAN",
        "CALCULATION_PLAN",
        "SUITABILITY_PLAN",
        "RECOMMENDATION_PLAN",
        "ADVISOR_COMMUNICATION_PLAN",
    }
)

EXECUTION_MODES = frozenset({"DIRECT_GROUNDED", "INTERPRETIVE", "DECISION_SUPPORT", "NO_EXECUTION"})

STEP_TYPES = frozenset(
    {
        "VALIDATE_REQUEST_CONTEXT",
        "RESOLVE_ENTITY_REFERENCES",
        "RESOLVE_DOCUMENT_REFERENCES",
        "RESOLVE_POLICY_FACTS",
        "RESOLVE_PRODUCT_FACTS",
        "RESOLVE_CLAUSE_EVIDENCE",
        "RESOLVE_COVERAGE_EVIDENCE",
        "RESOLVE_EXCLUSION_EVIDENCE",
        "RESOLVE_CLAIM_CONDITIONS",
        "RESOLVE_COMPARISON_DIMENSIONS",
        "RESOLVE_USER_OBJECTIVE",
        "RESOLVE_SCENARIO_INPUTS",
        "VALIDATE_EVIDENCE_SUFFICIENCY",
        "DETECT_EVIDENCE_CONFLICTS",
        "PERFORM_DETERMINISTIC_CALCULATION",
        "APPLY_DOMAIN_RULES",
        "DERIVE_INSURANCE_IMPLICATIONS",
        "COMPARE_OPTIONS",
        "ASSESS_SUITABILITY",
        "FORM_CONDITIONAL_RECOMMENDATION",
        "GENERATE_CONSUMER_EXPLANATION",
        "GENERATE_ADVISOR_EXPLANATION",
        "ASSEMBLE_EVIDENCE_TRACE",
        "APPLY_SAFETY_GATE",
    }
)

STEP_STATUS_VALUES = frozenset(
    {"PLANNED", "READY", "BLOCKED", "IN_PROGRESS", "COMPLETED", "FAILED", "SKIPPED"}
)

STAGE_OWNERS = frozenset(
    {"PLANNING", "EVIDENCE_RESOLVER", "REASONING_ENGINE", "SAFETY_GATE", "EXPLANATION_GENERATOR", "RESPONSE_ASSEMBLER"}
)

EVIDENCE_CATEGORIES = frozenset(
    {
        "POLICY_WORDING",
        "POLICY_SCHEDULE",
        "CUSTOMER_INFORMATION_SHEET",
        "ENDORSEMENT",
        "PROSPECTUS",
        "QUOTE",
        "BROCHURE",
        "OFFICIAL_PRODUCT_PAGE",
        "OFFICIAL_FAQ",
        "NORMALIZED_PRODUCT_FACT",
        "NORMALIZED_POLICY_FACT",
        "CLAUSE_TEXT",
        "USER_DOCUMENT",
        "EXTERNAL_REGULATORY_SOURCE",
        "EXTERNAL_FINANCIAL_SOURCE",
    }
)

AUTHORITY_REQUIREMENTS = frozenset({"BINDING", "AUTHORITATIVE", "OFFICIAL", "SUPPORTING", "ANY_GOVERNED"})
VERSION_REQUIREMENTS = frozenset(
    {"CURRENT_APPLICABLE", "POLICY_SPECIFIC", "REQUEST_DATE_APPLICABLE", "LATEST_AVAILABLE", "ANY_GOVERNED"}
)

CALCULATION_TYPES = frozenset(
    {
        "PERCENTAGE_AMOUNT",
        "COPAY_AMOUNT",
        "DEDUCTIBLE_SHORTFALL",
        "WAITING_PERIOD_END_DATE",
        "CLAIM_CONTRIBUTION",
        "COVERAGE_GAP",
        "CUMULATIVE_COVERAGE",
        "PREMIUM_DIFFERENCE",
        "AGE_AT_DATE",
        "TIME_PERIOD_ELAPSED",
        "NO_CALCULATION",
    }
)

DOMAIN_CAPABILITIES = frozenset(
    {
        "HEALTH_TERM_EXPLANATION",
        "HEALTH_POLICY_FACT_LOOKUP",
        "HEALTH_COVERAGE_ANALYSIS",
        "HEALTH_EXCLUSION_ANALYSIS",
        "HEALTH_CLAUSE_IMPLICATION",
        "HEALTH_CLAIM_SCENARIO",
        "HEALTH_PRODUCT_EXPLANATION",
        "HEALTH_PRODUCT_COMPARISON",
        "HEALTH_QUOTE_COMPARISON",
        "HEALTH_BASE_VS_TOPUP_ANALYSIS",
        "HEALTH_SUITABILITY_ASSESSMENT",
        "HEALTH_ADVISOR_EXPLANATION",
    }
)

PLAN_STATUS_VALUES = frozenset(
    {
        "READY",
        "READY_WITH_LIMITATIONS",
        "CLARIFICATION_REQUIRED",
        "PARTIAL_PLAN",
        "NOT_PLANNABLE",
        "OUT_OF_SCOPE",
        "INVALID_INPUT",
    }
)

EXPECTED_OUTCOME_TYPES = frozenset(
    {
        "DIRECT_FACT_RESPONSE",
        "GENERAL_EXPLANATION",
        "PRODUCT_SPECIFIC_EXPLANATION",
        "CLAUSE_IMPACT_EXPLANATION",
        "COMPARISON_RESULT",
        "SCENARIO_RESULT",
        "CALCULATION_RESULT",
        "EDUCATIONAL_COMPARISON",
        "CONDITIONAL_RECOMMENDATION",
        "ADVISOR_EXPLANATION",
        "CLARIFICATION_REQUEST",
        "PARTIAL_RESPONSE",
        "ABSTENTION",
        "OUT_OF_SCOPE_RESPONSE",
    }
)

STOP_CONDITION_TYPES = frozenset(
    {
        "MISSING_REQUIRED_CONTEXT",
        "UNRESOLVED_CONTEXT_CONFLICT",
        "UNRESOLVED_ENTITY_REFERENCE",
        "REQUIRED_DOCUMENT_FAILED",
        "REQUIRED_EVIDENCE_MISSING",
        "EVIDENCE_CONFLICT_UNRESOLVED",
        "CALCULATION_INPUT_MISSING",
        "UNSUPPORTED_DOMAIN_CAPABILITY",
        "SAFETY_REVIEW_REQUIRED",
        "OUT_OF_SCOPE_REQUEST",
        "INVALID_CONTRACT",
    }
)

STOP_CONDITION_LIFECYCLE = frozenset({"ACTIVE_STOP_CONDITION", "PLANNED_FUTURE_CHECK"})

CLASSIFICATION_BASIS_VALUES = frozenset(
    {
        "intent_plan_mapping",
        "context_answerability",
        "selected_template",
        "partial_context_rule",
        "active_stop_condition",
        "inherited_assumption",
        "inherited_conflict",
        "execution_mode_rule",
        "domain_capability_mapping",
    }
)


class ReasoningPlannerError(ValueError):
    """Raised when a planning contract value is structurally or semantically invalid."""


def _require_nonempty_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReasoningPlannerError(f"{label} must be a non-empty string")
    return value


def _require_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ReasoningPlannerError(f"{label} must be a boolean")
    return value


def _require_bounded_float(value: object, label: str, *, low: float = 0.0, high: float = 1.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReasoningPlannerError(f"{label} must be a number")
    numeric = float(value)
    if not (low <= numeric <= high):
        raise ReasoningPlannerError(f"{label} must be between {low} and {high}; got {numeric}")
    return numeric


def _require_member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise ReasoningPlannerError(f"{label} must be one of {sorted(allowed)}; got {value!r}")
    return value  # type: ignore[return-value]


def _require_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReasoningPlannerError(f"{label} must be an integer")
    return value


# --- Input contract ----------------------------------------------------------


@dataclass(frozen=True)
class ReasoningPlannerInput:
    contract_version: str
    request_id: str
    intent_analysis: IntentAnalyzerOutput
    context_assessment: ContextBuilderOutput
    domain: str
    planning_mode: str


def build_input(
    *,
    request_id: str,
    intent_analysis: IntentAnalyzerOutput,
    context_assessment: ContextBuilderOutput,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
    domain: str = "unknown",
    planning_mode: str = "AUTO",
) -> ReasoningPlannerInput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise ReasoningPlannerError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}; got {contract_version!r}")
    if not isinstance(intent_analysis, IntentAnalyzerOutput):
        raise ReasoningPlannerError("intent_analysis must be a validated IntentAnalyzerOutput")
    if not isinstance(context_assessment, ContextBuilderOutput):
        raise ReasoningPlannerError("context_assessment must be a validated ContextBuilderOutput")
    validated_request_id = _require_nonempty_str(request_id, "request_id")
    if intent_analysis.request_id != validated_request_id or context_assessment.request_id != validated_request_id:
        raise ReasoningPlannerError(
            "request_id must match across intent_analysis, context_assessment, and this input"
        )
    return ReasoningPlannerInput(
        contract_version=contract_version,
        request_id=validated_request_id,
        intent_analysis=intent_analysis,
        context_assessment=context_assessment,
        domain=_require_member(domain, DOMAIN_VALUES, "domain"),
        planning_mode=_require_member(planning_mode, PLANNING_MODE_VALUES, "planning_mode"),
    )


# --- Plan step sub-contracts --------------------------------------------------


@dataclass(frozen=True)
class EvidenceRequirement:
    requirement_id: str
    evidence_category: str
    subject_reference: str
    required: bool
    authority_requirement: str
    version_requirement: str
    effective_date_requirement: str
    reason: str
    requested_by_step: str


def build_evidence_requirement(
    *,
    requirement_id: str,
    evidence_category: str,
    subject_reference: str,
    required: bool,
    authority_requirement: str,
    version_requirement: str,
    reason: str,
    requested_by_step: str,
    effective_date_requirement: str = "REQUEST_DATE_APPLICABLE",
) -> EvidenceRequirement:
    return EvidenceRequirement(
        requirement_id=_require_nonempty_str(requirement_id, "evidence_requirement.requirement_id"),
        evidence_category=_require_member(evidence_category, EVIDENCE_CATEGORIES, "evidence_requirement.evidence_category"),
        subject_reference=_require_nonempty_str(subject_reference, "evidence_requirement.subject_reference"),
        required=_require_bool(required, "evidence_requirement.required"),
        authority_requirement=_require_member(
            authority_requirement, AUTHORITY_REQUIREMENTS, "evidence_requirement.authority_requirement"
        ),
        version_requirement=_require_member(
            version_requirement, VERSION_REQUIREMENTS, "evidence_requirement.version_requirement"
        ),
        effective_date_requirement=_require_nonempty_str(
            effective_date_requirement, "evidence_requirement.effective_date_requirement"
        ),
        reason=_require_nonempty_str(reason, "evidence_requirement.reason"),
        requested_by_step=_require_nonempty_str(requested_by_step, "evidence_requirement.requested_by_step"),
    )


@dataclass(frozen=True)
class CalculationRequirement:
    calculation_id: str
    calculation_type: str
    required_inputs: tuple[str, ...]
    required: bool
    reason: str
    requested_by_step: str


def build_calculation_requirement(
    *,
    calculation_id: str,
    calculation_type: str,
    required_inputs: Sequence[str],
    required: bool,
    reason: str,
    requested_by_step: str,
) -> CalculationRequirement:
    return CalculationRequirement(
        calculation_id=_require_nonempty_str(calculation_id, "calculation_requirement.calculation_id"),
        calculation_type=_require_member(calculation_type, CALCULATION_TYPES, "calculation_requirement.calculation_type"),
        required_inputs=tuple(required_inputs),
        required=_require_bool(required, "calculation_requirement.required"),
        reason=_require_nonempty_str(reason, "calculation_requirement.reason"),
        requested_by_step=_require_nonempty_str(requested_by_step, "calculation_requirement.requested_by_step"),
    )


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    step_type: str
    sequence: int
    required: bool
    dependencies: tuple[str, ...]
    input_keys: tuple[str, ...]
    output_keys: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    calculation_requirements: tuple[str, ...]
    capability_requirements: tuple[str, ...]
    stop_on_failure: bool
    status: str


def build_plan_step(
    *,
    step_id: str,
    step_type: str,
    sequence: int,
    required: bool = True,
    dependencies: Sequence[str] = (),
    input_keys: Sequence[str] = (),
    output_keys: Sequence[str] = (),
    evidence_requirements: Sequence[str] = (),
    calculation_requirements: Sequence[str] = (),
    capability_requirements: Sequence[str] = (),
    stop_on_failure: bool = True,
    status: str = "PLANNED",
) -> PlanStep:
    return PlanStep(
        step_id=_require_nonempty_str(step_id, "plan_step.step_id"),
        step_type=_require_member(step_type, STEP_TYPES, "plan_step.step_type"),
        sequence=_require_int(sequence, "plan_step.sequence"),
        required=_require_bool(required, "plan_step.required"),
        dependencies=tuple(dependencies),
        input_keys=tuple(input_keys),
        output_keys=tuple(output_keys),
        evidence_requirements=tuple(evidence_requirements),
        calculation_requirements=tuple(calculation_requirements),
        capability_requirements=tuple(capability_requirements),
        stop_on_failure=_require_bool(stop_on_failure, "plan_step.stop_on_failure"),
        status=_require_member(status, STEP_STATUS_VALUES, "plan_step.status"),
    )


@dataclass(frozen=True)
class StopCondition:
    condition_type: str
    description: str
    blocking: bool
    source_stage: str
    related_keys: tuple[str, ...]
    required_resolution: str
    lifecycle: str


def build_stop_condition(
    *,
    condition_type: str,
    description: str,
    blocking: bool,
    source_stage: str,
    required_resolution: str,
    related_keys: Sequence[str] = (),
    lifecycle: str = "ACTIVE_STOP_CONDITION",
) -> StopCondition:
    return StopCondition(
        condition_type=_require_member(condition_type, STOP_CONDITION_TYPES, "stop_condition.condition_type"),
        description=_require_nonempty_str(description, "stop_condition.description"),
        blocking=_require_bool(blocking, "stop_condition.blocking"),
        source_stage=_require_nonempty_str(source_stage, "stop_condition.source_stage"),
        related_keys=tuple(related_keys),
        required_resolution=_require_nonempty_str(required_resolution, "stop_condition.required_resolution"),
        lifecycle=_require_member(lifecycle, STOP_CONDITION_LIFECYCLE, "stop_condition.lifecycle"),
    )


# --- Output contract -----------------------------------------------------------


@dataclass(frozen=True)
class ReasoningPlan:
    contract_version: str
    request_id: str
    plan_id: str
    plan_type: str
    execution_mode: str
    goal: str
    steps: tuple[PlanStep, ...]
    required_evidence: tuple[EvidenceRequirement, ...]
    required_calculations: tuple[CalculationRequirement, ...]
    required_capabilities: tuple[str, ...]
    inherited_assumptions: tuple[str, ...]
    inherited_conflicts: tuple[str, ...]
    limitations: tuple[str, ...]
    stop_conditions: tuple[StopCondition, ...]
    expected_outcome: str
    plan_status: str
    classification_basis: tuple[str, ...]
    confidence: float


def build_plan(
    *,
    request_id: str,
    plan_id: str,
    plan_type: str,
    execution_mode: str,
    goal: str,
    expected_outcome: str,
    plan_status: str,
    confidence: float,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
    steps: Sequence[PlanStep] = (),
    required_evidence: Sequence[EvidenceRequirement] = (),
    required_calculations: Sequence[CalculationRequirement] = (),
    required_capabilities: Sequence[str] = (),
    inherited_assumptions: Sequence[str] = (),
    inherited_conflicts: Sequence[str] = (),
    limitations: Sequence[str] = (),
    stop_conditions: Sequence[StopCondition] = (),
    classification_basis: Sequence[str] = (),
) -> ReasoningPlan:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise ReasoningPlannerError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}; got {contract_version!r}")
    validated_request_id = _require_nonempty_str(request_id, "request_id")
    validated_plan_id = _require_nonempty_str(plan_id, "plan_id")
    validated_plan_type = _require_member(plan_type, PLAN_TYPES, "plan_type")
    validated_execution_mode = _require_member(execution_mode, EXECUTION_MODES, "execution_mode")
    validated_goal = _require_nonempty_str(goal, "goal")
    validated_outcome = _require_member(expected_outcome, EXPECTED_OUTCOME_TYPES, "expected_outcome")
    validated_status = _require_member(plan_status, PLAN_STATUS_VALUES, "plan_status")
    validated_confidence = _require_bounded_float(confidence, "confidence")

    step_ids = [step.step_id for step in steps]
    if len(step_ids) != len(set(step_ids)):
        raise ReasoningPlannerError("plan step_id values must be unique")
    sequences = [step.sequence for step in steps]
    if len(sequences) != len(set(sequences)):
        raise ReasoningPlannerError("plan step sequence values must be unique")
    for step in steps:
        for dependency in step.dependencies:
            if dependency not in step_ids:
                raise ReasoningPlannerError(f"step {step.step_id} depends on unknown step {dependency}")
            dep_step = next(s for s in steps if s.step_id == dependency)
            if dep_step.sequence >= step.sequence:
                raise ReasoningPlannerError(
                    f"step {step.step_id} depends on {dependency}, which does not precede it (no circular/forward dependency)"
                )

    validated_basis: list[str] = []
    for basis in classification_basis:
        validated_basis.append(_require_member(basis, CLASSIFICATION_BASIS_VALUES, "classification_basis[]"))

    return ReasoningPlan(
        contract_version=contract_version,
        request_id=validated_request_id,
        plan_id=validated_plan_id,
        plan_type=validated_plan_type,
        execution_mode=validated_execution_mode,
        goal=validated_goal,
        steps=tuple(steps),
        required_evidence=tuple(required_evidence),
        required_calculations=tuple(required_calculations),
        required_capabilities=tuple(required_capabilities),
        inherited_assumptions=tuple(inherited_assumptions),
        inherited_conflicts=tuple(inherited_conflicts),
        limitations=tuple(limitations),
        stop_conditions=tuple(stop_conditions),
        expected_outcome=validated_outcome,
        plan_status=validated_status,
        classification_basis=tuple(validated_basis),
        confidence=validated_confidence,
    )
