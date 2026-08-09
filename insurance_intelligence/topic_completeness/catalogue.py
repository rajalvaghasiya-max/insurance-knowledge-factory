"""Generic insurer-independent topic definitions (MO-023I.4)."""

from __future__ import annotations

from insurance_intelligence.contracts.topic_completeness import (
    TopicDefinition,
    build_component_definition,
    build_topic_definition,
)
from insurance_intelligence.topic_completeness.registry import (
    TopicCompletenessRegistry,
)

CATALOGUE_VERSION = "1.0"


def _component(
    component_id: str,
    requirement_type: str,
    *,
    required: bool = True,
    dependencies: tuple[str, ...] = (),
    authority: str = "AUTHORITATIVE",
    roles: tuple[str, ...] = ("SUPPORTING", "DEFINING", "QUALIFYING"),
    statuses: tuple[str, ...] = ("SATISFIED", "SATISFIED_WITH_LIMITATIONS"),
    reason: str,
):
    return build_component_definition(
        component_id=component_id,
        requirement_type=requirement_type,
        required=required,
        acceptable_requirement_statuses=statuses,
        acceptable_evidence_roles=roles,
        minimum_authority=authority,
        dependency_component_ids=dependencies,
        reason=reason,
    )


def build_conditional_obligation_definition() -> TopicDefinition:
    return build_topic_definition(
        topic_id="conditional_obligation",
        topic_version=CATALOGUE_VERSION,
        domain="health",
        components=(
            _component(
                "obligation_value",
                "OBLIGATION_VALUE",
                reason="Resolve the amount, percentage, duration, or action imposed.",
            ),
            _component(
                "trigger_condition",
                "TRIGGER_CONDITION",
                reason="Resolve the condition that activates the obligation.",
            ),
            _component(
                "applicability_scope",
                "APPLICABILITY_SCOPE",
                reason="Resolve the persons, events, services, or policy scope affected.",
            ),
            _component(
                "exception_condition",
                "EXCEPTION_CONDITION",
                required=False,
                dependencies=("trigger_condition",),
                reason="Resolve any exception that limits or disables the trigger.",
            ),
            _component(
                "calculation_basis",
                "CALCULATION_BASIS",
                required=False,
                dependencies=("obligation_value",),
                roles=("SUPPORTING", "DEFINING", "CALCULATION_INPUT"),
                reason="Resolve the basis used to calculate the obligation.",
            ),
        ),
    )


def build_eligibility_and_consequence_definition() -> TopicDefinition:
    return build_topic_definition(
        topic_id="eligibility_and_consequence",
        topic_version=CATALOGUE_VERSION,
        domain="health",
        components=(
            _component(
                "eligibility_criteria",
                "ELIGIBILITY_CRITERIA",
                reason="Resolve the criteria that determine eligibility.",
            ),
            _component(
                "applicability_scope",
                "APPLICABILITY_SCOPE",
                reason="Resolve the scope to which the eligibility rule applies.",
            ),
            _component(
                "eligible_consequence",
                "ELIGIBLE_CONSEQUENCE",
                dependencies=("eligibility_criteria",),
                reason="Resolve the consequence when eligibility is satisfied.",
            ),
            _component(
                "ineligible_consequence",
                "INELIGIBLE_CONSEQUENCE",
                dependencies=("eligibility_criteria",),
                reason="Resolve the consequence when eligibility is not satisfied.",
            ),
            _component(
                "exception_condition",
                "EXCEPTION_CONDITION",
                required=False,
                dependencies=("eligibility_criteria",),
                reason="Resolve any exception to the eligibility rule.",
            ),
        ),
    )


def build_coverage_limit_definition() -> TopicDefinition:
    return build_topic_definition(
        topic_id="coverage_limit",
        topic_version=CATALOGUE_VERSION,
        domain="health",
        components=(
            _component(
                "covered_subject",
                "COVERED_SUBJECT",
                reason="Resolve the benefit, service, event, or expense being limited.",
            ),
            _component(
                "limit_value",
                "LIMIT_VALUE",
                reason="Resolve the monetary, quantitative, temporal, or categorical limit.",
            ),
            _component(
                "limit_basis",
                "LIMIT_BASIS",
                dependencies=("limit_value",),
                reason="Resolve whether the limit applies per event, policy year, person, or another basis.",
            ),
            _component(
                "applicability_scope",
                "APPLICABILITY_SCOPE",
                reason="Resolve the scope affected by the limit.",
            ),
            _component(
                "excess_consequence",
                "EXCESS_CONSEQUENCE",
                required=False,
                dependencies=("limit_value", "limit_basis"),
                reason="Resolve what happens when the limit is exceeded.",
            ),
        ),
    )


def build_waiting_period_definition() -> TopicDefinition:
    return build_topic_definition(
        topic_id="waiting_period",
        topic_version=CATALOGUE_VERSION,
        domain="health",
        components=(
            _component(
                "waiting_period_duration",
                "WAITING_PERIOD_DURATION",
                reason="Resolve the duration of the waiting period.",
            ),
            _component(
                "waiting_period_subject",
                "WAITING_PERIOD_SUBJECT",
                reason="Resolve the condition, treatment, benefit, or event subject to waiting.",
            ),
            _component(
                "start_basis",
                "WAITING_PERIOD_START_BASIS",
                reason="Resolve the event or date from which the waiting period is measured.",
            ),
            _component(
                "applicability_scope",
                "APPLICABILITY_SCOPE",
                reason="Resolve the persons, policies, or circumstances affected.",
            ),
            _component(
                "continuity_or_credit_rule",
                "CONTINUITY_OR_CREDIT_RULE",
                required=False,
                dependencies=("waiting_period_duration", "start_basis"),
                reason="Resolve whether prior coverage or continuity changes the waiting period.",
            ),
            _component(
                "exception_condition",
                "EXCEPTION_CONDITION",
                required=False,
                dependencies=("waiting_period_subject",),
                reason="Resolve any waiver or exception to the waiting period.",
            ),
        ),
    )


def default_topic_definitions() -> tuple[TopicDefinition, ...]:
    """Return the validated default catalogue in deterministic topic order."""
    definitions = (
        build_conditional_obligation_definition(),
        build_coverage_limit_definition(),
        build_eligibility_and_consequence_definition(),
        build_waiting_period_definition(),
    )
    return tuple(sorted(definitions, key=lambda item: (item.domain, item.topic_id, item.topic_version)))


def build_default_topic_registry() -> TopicCompletenessRegistry:
    """Build a new registry with every catalogue definition active."""
    registry = TopicCompletenessRegistry()
    for definition in default_topic_definitions():
        registry.register(definition, active=True)
    return registry
