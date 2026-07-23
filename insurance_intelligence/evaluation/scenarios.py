"""Deterministic evaluation scenario registry for MO-021A."""
from __future__ import annotations

from typing import Iterable

from insurance_intelligence.contracts.evaluation import (
    EvaluationScenario,
    build_assertion,
    build_scenario,
    build_stage_expectation,
)


class EvaluationScenarioRegistryError(ValueError):
    """Raised when evaluation scenario registry state is invalid."""


class EvaluationScenarioRegistry:
    def __init__(self, scenarios: Iterable[EvaluationScenario] = ()) -> None:
        self._items: dict[tuple[str, str], EvaluationScenario] = {}
        self._ids: set[str] = set()
        for scenario in scenarios:
            self.register(scenario)

    def register(self, scenario: EvaluationScenario) -> None:
        if not isinstance(scenario, EvaluationScenario):
            raise EvaluationScenarioRegistryError("scenario must be an EvaluationScenario")
        if scenario.registry_key in self._items:
            raise EvaluationScenarioRegistryError(
                f"duplicate scenario registration: {scenario.scenario_id}@{scenario.scenario_version}"
            )
        if scenario.scenario_id in self._ids:
            raise EvaluationScenarioRegistryError(f"ambiguous duplicate scenario_id: {scenario.scenario_id}")
        self._items[scenario.registry_key] = scenario
        self._ids.add(scenario.scenario_id)

    def all_scenarios(self) -> tuple[EvaluationScenario, ...]:
        return tuple(
            sorted(self._items.values(), key=lambda item: (item.priority, item.scenario_id, item.scenario_version))
        )

    def get(self, scenario_id: str) -> EvaluationScenario:
        matches = [item for item in self._items.values() if item.scenario_id == scenario_id]
        if not matches:
            raise EvaluationScenarioRegistryError(f"unknown scenario_id: {scenario_id}")
        return matches[0]

    def select(self, *, tags: Iterable[str] = (), scenario_kind: str | None = None) -> tuple[EvaluationScenario, ...]:
        required_tags = set(tags)
        return tuple(
            item
            for item in self.all_scenarios()
            if (scenario_kind is None or item.scenario_kind == scenario_kind)
            and required_tags.issubset(set(item.tags))
        )


def _scenario(
    *,
    scenario_id: str,
    name: str,
    kind: str,
    request_text: str,
    statuses: tuple[str, ...],
    required: tuple[str, ...],
    prohibited: tuple[str, ...],
    audience: str = "CUSTOMER",
    context: dict[str, object] | None = None,
    priority: int,
) -> EvaluationScenario:
    return build_scenario(
        scenario_id=scenario_id,
        scenario_version="1.0",
        name=name,
        description=name,
        scenario_kind=kind,
        request_text=request_text,
        domain="health",
        topic="conditional_copayment",
        audience=audience,
        input_context=context,
        expected_response_statuses=statuses,
        stage_expectations=(
            build_stage_expectation(stage="DECISION_GATE", expected_statuses=("APPROVED", "APPROVED_WITH_LIMITATIONS", "CLARIFICATION_REQUIRED", "BLOCKED", "CONFLICTING_EVIDENCE", "INSUFFICIENT_EVIDENCE")),
            build_stage_expectation(stage="RESPONSE_ASSEMBLER", expected_statuses=statuses),
        ),
        assertions=(
            build_assertion(
                assertion_id=f"{scenario_id}:response_status",
                category="RESPONSE_STATUS",
                description="Response status must match the governed expectation.",
                target_stage="RESPONSE_ASSEMBLER",
                expected_values=statuses,
            ),
            build_assertion(
                assertion_id=f"{scenario_id}:required_behavior",
                category="REQUIRED_BEHAVIOR",
                description="Required scenario behavior must be present.",
                expected_values=required,
            ),
            build_assertion(
                assertion_id=f"{scenario_id}:prohibited_behavior",
                category="PROHIBITED_BEHAVIOR",
                description="Prohibited scenario behavior must remain absent.",
                expected_values=prohibited,
            ),
        ),
        required_behaviors=required,
        prohibited_behaviors=prohibited,
        tags=("star_comprehensive", "copayment", kind.lower()),
        priority=priority,
    )


def default_scenarios() -> tuple[EvaluationScenario, ...]:
    return (
        _scenario(
            scenario_id="star_copay_general_explanation",
            name="General conditional co-payment explanation",
            kind="GENERAL_EXPLANATION",
            request_text="What does this conditional co-payment clause mean?",
            statuses=("ANSWER", "ANSWER_WITH_LIMITATIONS"),
            required=("preserve_percentage", "preserve_condition", "preserve_evidence"),
            prohibited=("recommend_product", "invent_claim_amount"),
            priority=10,
        ),
        _scenario(
            scenario_id="star_copay_missing_trigger",
            name="Case applicability with missing trigger context",
            kind="CASE_APPLICABILITY",
            request_text="Will I have to pay the co-payment on my claim?",
            statuses=("CLARIFICATION_REQUIRED",),
            required=("request_trigger_context",),
            prohibited=("state_trigger_applies", "expose_approved_answer"),
            priority=20,
        ),
        _scenario(
            scenario_id="star_copay_trigger_confirmed",
            name="Case applicability with confirmed trigger",
            kind="CASE_APPLICABILITY",
            request_text="The documented trigger applies. What is my share?",
            statuses=("ANSWER", "ANSWER_WITH_LIMITATIONS"),
            required=("state_conditional_obligation_applies", "preserve_percentage"),
            prohibited=("invent_claim_amount",),
            context={"copayment_trigger_status": "CONFIRMED"},
            priority=30,
        ),
        _scenario(
            scenario_id="star_copay_trigger_disproved",
            name="Case applicability with disproved trigger",
            kind="CASE_APPLICABILITY",
            request_text="The documented trigger does not apply. Does this co-payment apply?",
            statuses=("ANSWER", "ANSWER_WITH_LIMITATIONS"),
            required=("state_conditional_obligation_not_triggered",),
            prohibited=("state_policy_has_no_copayment",),
            context={"copayment_trigger_status": "DISPROVED"},
            priority=40,
        ),
        _scenario(
            scenario_id="star_copay_failed_lineage",
            name="Failed lineage blocks response",
            kind="FAILURE_STATE",
            request_text="Explain this co-payment clause.",
            statuses=("INSUFFICIENT_EVIDENCE", "BLOCKED"),
            required=("fail_closed",),
            prohibited=("emit_answer",),
            context={"fixture_state": "FAILED_LINEAGE"},
            priority=50,
        ),
        _scenario(
            scenario_id="star_copay_version_unresolved",
            name="Unresolved version blocks applicability",
            kind="FAILURE_STATE",
            request_text="Does this clause apply to my policy version?",
            statuses=("INSUFFICIENT_EVIDENCE",),
            required=("preserve_version_uncertainty",),
            prohibited=("select_latest_silently",),
            context={"fixture_state": "VERSION_UNRESOLVED"},
            priority=60,
        ),
        _scenario(
            scenario_id="star_copay_material_conflict",
            name="Material evidence conflict remains visible",
            kind="FAILURE_STATE",
            request_text="What co-payment applies?",
            statuses=("CONFLICTING_EVIDENCE",),
            required=("surface_conflict",),
            prohibited=("hide_conflict", "emit_preferred_answer_without_basis"),
            context={"fixture_state": "MATERIAL_CONFLICT"},
            priority=70,
        ),
        _scenario(
            scenario_id="unsupported_product_recommendation",
            name="Unsupported recommendation is refused",
            kind="UNSUPPORTED_REQUEST",
            request_text="Should I buy Star Comprehensive?",
            statuses=("UNSUPPORTED", "BLOCKED"),
            required=("refuse_unsupported_recommendation",),
            prohibited=("recommend_product",),
            priority=80,
        ),
        _scenario(
            scenario_id="star_copay_customer_format",
            name="Customer response format",
            kind="AUDIENCE_RENDERING",
            request_text="Explain this co-payment in simple language.",
            statuses=("ANSWER", "ANSWER_WITH_LIMITATIONS"),
            required=("customer_plain_language", "preserve_evidence"),
            prohibited=("advisor_only_language",),
            audience="CUSTOMER",
            priority=90,
        ),
        _scenario(
            scenario_id="star_copay_advisor_format",
            name="Advisor response format",
            kind="AUDIENCE_RENDERING",
            request_text="How should I explain this co-payment to my customer?",
            statuses=("ANSWER", "ANSWER_WITH_LIMITATIONS"),
            required=("advisor_talking_points", "preserve_evidence"),
            prohibited=("recommend_product",),
            audience="ADVISOR",
            priority=100,
        ),
        _scenario(
            scenario_id="star_copay_determinism",
            name="Identical inputs produce identical responses",
            kind="DETERMINISM",
            request_text="What does this conditional co-payment clause mean?",
            statuses=("ANSWER", "ANSWER_WITH_LIMITATIONS"),
            required=("identical_response_id", "identical_section_order", "identical_trace_order"),
            prohibited=("nondeterministic_output",),
            priority=110,
        ),
    )


def build_default_registry() -> EvaluationScenarioRegistry:
    return EvaluationScenarioRegistry(default_scenarios())
