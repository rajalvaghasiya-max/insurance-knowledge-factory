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
    query_aliases: tuple[str, ...] = (),
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
        query_aliases=query_aliases,
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
                query_aliases=("how much", "what percentage", "what amount", "what is the obligation"),
                reason="Resolve the amount, percentage, duration, or action imposed.",
            ),
            _component(
                "trigger_condition",
                "TRIGGER_CONDITION",
                query_aliases=("what triggers", "trigger condition", "when does this apply"),
                reason="Resolve the condition that activates the obligation.",
            ),
            _component(
                "applicability_scope",
                "APPLICABILITY_SCOPE",
                query_aliases=("who does this apply to", "which services", "which events", "applicability scope"),
                reason="Resolve the persons, events, services, or policy scope affected.",
            ),
            _component(
                "exception_condition",
                "EXCEPTION_CONDITION",
                required=False,
                dependencies=("trigger_condition",),
                query_aliases=("exception", "waiver"),
                reason="Resolve any exception that limits or disables the trigger.",
            ),
            _component(
                "calculation_basis",
                "CALCULATION_BASIS",
                required=False,
                dependencies=("obligation_value",),
                roles=("SUPPORTING", "DEFINING", "CALCULATION_INPUT"),
                query_aliases=("calculation basis", "how is it calculated"),
                reason="Resolve the basis used to calculate the obligation.",
            ),
        ),
        default_direct_component_id="obligation_value",
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
                query_aliases=("who is eligible", "eligibility criteria"),
                reason="Resolve the criteria that determine eligibility.",
            ),
            _component(
                "applicability_scope",
                "APPLICABILITY_SCOPE",
                query_aliases=("who does this eligibility rule apply to", "applicability scope"),
                reason="Resolve the scope to which the eligibility rule applies.",
            ),
            _component(
                "eligible_consequence",
                "ELIGIBLE_CONSEQUENCE",
                dependencies=("eligibility_criteria",),
                query_aliases=("what happens if eligible",),
                reason="Resolve the consequence when eligibility is satisfied.",
            ),
            _component(
                "ineligible_consequence",
                "INELIGIBLE_CONSEQUENCE",
                dependencies=("eligibility_criteria",),
                query_aliases=("what happens if not eligible", "what happens if ineligible"),
                reason="Resolve the consequence when eligibility is not satisfied.",
            ),
            _component(
                "exception_condition",
                "EXCEPTION_CONDITION",
                required=False,
                dependencies=("eligibility_criteria",),
                query_aliases=("exception", "waiver"),
                reason="Resolve any exception to the eligibility rule.",
            ),
        ),
        default_direct_component_id="eligibility_criteria",
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
                query_aliases=("what is limited", "which benefit is limited", "covered subject"),
                reason="Resolve the benefit, service, event, or expense being limited.",
            ),
            _component(
                "limit_value",
                "LIMIT_VALUE",
                query_aliases=("how much is the limit", "what is the limit", "limit value"),
                reason="Resolve the monetary, quantitative, temporal, or categorical limit.",
            ),
            _component(
                "limit_basis",
                "LIMIT_BASIS",
                dependencies=("limit_value",),
                query_aliases=("basis of this coverage limit", "limit basis", "per event", "per year"),
                reason="Resolve whether the limit applies per event, policy year, person, or another basis.",
            ),
            _component(
                "applicability_scope",
                "APPLICABILITY_SCOPE",
                query_aliases=("who does the limit apply to", "applicability scope"),
                reason="Resolve the scope affected by the limit.",
            ),
            _component(
                "excess_consequence",
                "EXCESS_CONSEQUENCE",
                required=False,
                dependencies=("limit_value", "limit_basis"),
                query_aliases=("what happens if the limit is exceeded", "exceed the limit"),
                reason="Resolve what happens when the limit is exceeded.",
            ),
        ),
        default_direct_component_id="limit_value",
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
                query_aliases=("how long", "duration of the waiting period", "waiting period duration"),
                reason="Resolve the duration of the waiting period.",
            ),
            _component(
                "waiting_period_subject",
                "WAITING_PERIOD_SUBJECT",
                query_aliases=(
                    "what does the waiting period apply to",
                    "what is subject to the waiting period",
                    "which conditions are subject to the waiting period",
                ),
                reason="Resolve the condition, treatment, benefit, or event subject to waiting.",
            ),
            _component(
                "start_basis",
                "WAITING_PERIOD_START_BASIS",
                query_aliases=("when does the waiting period start", "when does it start", "start basis", "measured from"),
                reason="Resolve the event or date from which the waiting period is measured.",
            ),
            _component(
                "applicability_scope",
                "APPLICABILITY_SCOPE",
                query_aliases=("who does the waiting period apply to", "which policies does the waiting period apply to", "applicability scope"),
                reason="Resolve the persons, policies, or circumstances affected.",
            ),
            _component(
                "continuity_or_credit_rule",
                "CONTINUITY_OR_CREDIT_RULE",
                required=False,
                dependencies=("waiting_period_duration", "start_basis"),
                query_aliases=("portability", "prior coverage", "continuity"),
                reason="Resolve whether prior coverage or continuity changes the waiting period.",
            ),
            _component(
                "exception_condition",
                "EXCEPTION_CONDITION",
                required=False,
                dependencies=("waiting_period_subject",),
                query_aliases=("exception", "waiver"),
                reason="Resolve any waiver or exception to the waiting period.",
            ),
        ),
        default_direct_component_id="waiting_period_duration",
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
