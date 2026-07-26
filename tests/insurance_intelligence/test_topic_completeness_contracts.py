from __future__ import annotations

import pytest

from insurance_intelligence.contracts.topic_completeness import (
    TopicCompletenessContractError,
    build_completeness_result,
    build_component_definition,
    build_component_result,
    build_topic_definition,
)


def _component(
    component_id: str,
    *,
    required: bool = True,
    dependencies: tuple[str, ...] = (),
):
    return build_component_definition(
        component_id=component_id,
        requirement_type=f"{component_id.upper()}_REQUIREMENT",
        required=required,
        acceptable_requirement_statuses=("SATISFIED",),
        acceptable_evidence_roles=("SUPPORTING",),
        minimum_authority="AUTHORITATIVE",
        dependency_component_ids=dependencies,
        reason=f"Resolve {component_id}.",
    )


def _definition():
    return build_topic_definition(
        topic_id="generic_conditional_obligation",
        topic_version="1.0",
        domain="health",
        components=(
            _component("obligation_value"),
            _component("trigger_condition"),
            _component(
                "exception_condition",
                dependencies=("trigger_condition",),
            ),
            _component("worked_example", required=False),
        ),
    )


def _satisfied(component_id: str):
    return build_component_result(
        component_id=component_id,
        status="SATISFIED",
        matched_requirement_ids=(f"req:{component_id}",),
        matched_evidence_ids=(f"ev:{component_id}",),
        confidence=1.0,
    )


def test_builds_insurer_independent_topic_definition():
    definition = _definition()

    assert definition.topic_id == "generic_conditional_obligation"
    assert definition.domain == "health"
    assert definition.minimum_required_components == 3
    assert all("star" not in component.component_id for component in definition.components)


def test_rejects_duplicate_component_ids():
    with pytest.raises(
        TopicCompletenessContractError,
        match="component_id values must be unique",
    ):
        build_topic_definition(
            topic_id="duplicate_topic",
            topic_version="1.0",
            domain="health",
            components=(_component("scope"), _component("scope")),
        )


def test_rejects_unknown_component_dependency():
    with pytest.raises(
        TopicCompletenessContractError,
        match="unknown dependencies",
    ):
        build_topic_definition(
            topic_id="unknown_dependency",
            topic_version="1.0",
            domain="health",
            components=(_component("scope", dependencies=("missing",)),),
        )


def test_rejects_direct_self_dependency():
    with pytest.raises(
        TopicCompletenessContractError,
        match="component cannot depend on itself",
    ):
        _component("scope", dependencies=("scope",))


def test_rejects_circular_component_dependencies():
    with pytest.raises(
        TopicCompletenessContractError,
        match="must not contain cycles",
    ):
        build_topic_definition(
            topic_id="cycle",
            topic_version="1.0",
            domain="health",
            components=(
                _component("trigger", dependencies=("exception",)),
                _component("exception", dependencies=("trigger",)),
            ),
        )


def test_requires_at_least_one_required_component():
    with pytest.raises(
        TopicCompletenessContractError,
        match="at least one required component",
    ):
        build_topic_definition(
            topic_id="optional_only",
            topic_version="1.0",
            domain="health",
            components=(_component("example", required=False),),
        )


def test_cannot_weaken_required_component_count():
    with pytest.raises(
        TopicCompletenessContractError,
        match="must equal the number of required components",
    ):
        build_topic_definition(
            topic_id="weakened",
            topic_version="1.0",
            domain="health",
            components=(_component("value"), _component("scope")),
            minimum_required_components=1,
        )


def test_satisfied_component_requires_requirement_and_evidence_references():
    with pytest.raises(
        TopicCompletenessContractError,
        match="at least one requirement",
    ):
        build_component_result(
            component_id="value",
            status="SATISFIED",
            matched_evidence_ids=("ev:value",),
            confidence=1.0,
        )

    with pytest.raises(
        TopicCompletenessContractError,
        match="at least one evidence",
    ):
        build_component_result(
            component_id="value",
            status="SATISFIED",
            matched_requirement_ids=("req:value",),
            confidence=1.0,
        )


def test_limited_component_requires_explicit_limitation():
    with pytest.raises(
        TopicCompletenessContractError,
        match="requires at least one limitation",
    ):
        build_component_result(
            component_id="value",
            status="SATISFIED_WITH_LIMITATIONS",
            matched_requirement_ids=("req:value",),
            matched_evidence_ids=("ev:value",),
            confidence=0.8,
        )


def test_rejects_confidence_outside_unit_interval():
    with pytest.raises(
        TopicCompletenessContractError,
        match="between 0.0 and 1.0",
    ):
        build_component_result(
            component_id="value",
            status="MISSING",
            confidence=1.1,
        )


def test_complete_result_requires_every_required_component_satisfied():
    definition = _definition()
    results = (
        _satisfied("obligation_value"),
        _satisfied("trigger_condition"),
        _satisfied("exception_condition"),
        build_component_result(
            component_id="worked_example",
            status="NOT_APPLICABLE",
            confidence=1.0,
        ),
    )

    output = build_completeness_result(
        definition=definition,
        request_id="req-1",
        status="COMPLETE",
        component_results=results,
        explanation_permitted=True,
        confidence=1.0,
    )

    assert output.status == "COMPLETE"
    assert output.explanation_permitted is True
    assert output.missing_required_components == ()


def test_complete_rejects_missing_component_result():
    definition = _definition()

    with pytest.raises(
        TopicCompletenessContractError,
        match="result for every defined component",
    ):
        build_completeness_result(
            definition=definition,
            request_id="req-1",
            status="COMPLETE",
            component_results=(
                _satisfied("obligation_value"),
                _satisfied("trigger_condition"),
                _satisfied("exception_condition"),
            ),
            explanation_permitted=True,
            confidence=1.0,
        )


def test_missing_required_components_must_be_explicit_and_exact():
    definition = _definition()
    results = (
        _satisfied("obligation_value"),
        _satisfied("trigger_condition"),
        build_component_result(
            component_id="exception_condition",
            status="MISSING",
            confidence=0.0,
        ),
    )

    with pytest.raises(
        TopicCompletenessContractError,
        match="must exactly match",
    ):
        build_completeness_result(
            definition=definition,
            request_id="req-1",
            status="PARTIAL",
            component_results=results,
            explanation_permitted=False,
            confidence=0.5,
        )

    output = build_completeness_result(
        definition=definition,
        request_id="req-1",
        status="PARTIAL",
        component_results=results,
        missing_required_components=("exception_condition",),
        explanation_permitted=False,
        confidence=0.5,
    )

    assert output.missing_required_components == ("exception_condition",)


def test_conflicting_components_must_be_explicit_and_exact():
    definition = _definition()
    results = (
        _satisfied("obligation_value"),
        _satisfied("trigger_condition"),
        build_component_result(
            component_id="exception_condition",
            status="CONFLICTING",
            confidence=0.4,
        ),
    )

    output = build_completeness_result(
        definition=definition,
        request_id="req-1",
        status="CONFLICTING",
        component_results=results,
        conflicting_components=("exception_condition",),
        explanation_permitted=False,
        confidence=0.4,
    )

    assert output.conflicting_components == ("exception_condition",)


def test_unknown_result_component_is_rejected():
    definition = _definition()

    with pytest.raises(
        TopicCompletenessContractError,
        match="unknown components",
    ):
        build_completeness_result(
            definition=definition,
            request_id="req-1",
            status="PARTIAL",
            component_results=(
                build_component_result(
                    component_id="insurer_specific_field",
                    status="MISSING",
                    confidence=0.0,
                ),
            ),
            missing_required_components=(),
            explanation_permitted=False,
            confidence=0.0,
        )


@pytest.mark.parametrize(
    "status",
    [
        "CONFLICTING",
        "NOT_AVAILABLE",
        "CLARIFICATION_REQUIRED",
        "INVALID_INPUT",
    ],
)
def test_blocking_statuses_cannot_permit_explanation(status: str):
    definition = _definition()

    if status == "CONFLICTING":
        results = (
            build_component_result(
                component_id="obligation_value",
                status="CONFLICTING",
                confidence=0.2,
            ),
        )
        kwargs = {
            "missing_required_components": (
                "trigger_condition",
                "exception_condition",
            ),
            "conflicting_components": ("obligation_value",),
        }
    elif status == "CLARIFICATION_REQUIRED":
        results = (
            build_component_result(
                component_id="obligation_value",
                status="UNRESOLVED",
                confidence=0.2,
            ),
        )
        kwargs = {
            "missing_required_components": (
                "trigger_condition",
                "exception_condition",
            ),
            "unresolved_components": ("obligation_value",),
        }
    else:
        results = ()
        kwargs = {
            "missing_required_components": (
                "obligation_value",
                "trigger_condition",
                "exception_condition",
            )
        }

    with pytest.raises(
        TopicCompletenessContractError,
        match="explanation_permitted cannot be true",
    ):
        build_completeness_result(
            definition=definition,
            request_id="req-1",
            status=status,
            component_results=results,
            explanation_permitted=True,
            confidence=0.2,
            **kwargs,
        )


def test_complete_with_limitations_requires_limited_component():
    definition = _definition()
    results = (
        _satisfied("obligation_value"),
        _satisfied("trigger_condition"),
        build_component_result(
            component_id="exception_condition",
            status="SATISFIED_WITH_LIMITATIONS",
            matched_requirement_ids=("req:exception_condition",),
            matched_evidence_ids=("ev:exception_condition",),
            limitations=("Policy-specific schedule not supplied.",),
            confidence=0.8,
        ),
        build_component_result(
            component_id="worked_example",
            status="NOT_APPLICABLE",
            confidence=1.0,
        ),
    )

    output = build_completeness_result(
        definition=definition,
        request_id="req-1",
        status="COMPLETE_WITH_LIMITATIONS",
        component_results=results,
        limitations=("One component is resolved with limitations.",),
        explanation_permitted=True,
        confidence=0.8,
    )

    assert output.status == "COMPLETE_WITH_LIMITATIONS"


def test_result_uses_definition_topic_identity_and_version():
    definition = _definition()
    results = (
        _satisfied("obligation_value"),
        _satisfied("trigger_condition"),
        _satisfied("exception_condition"),
        build_component_result(
            component_id="worked_example",
            status="NOT_APPLICABLE",
            confidence=1.0,
        ),
    )

    output = build_completeness_result(
        definition=definition,
        request_id="req-identity",
        status="COMPLETE",
        component_results=results,
        explanation_permitted=True,
        confidence=1.0,
    )

    assert output.topic_id == definition.topic_id
    assert output.topic_version == definition.topic_version
    assert output.contract_version == definition.contract_version
