from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.response import registry as rr


def _answer(**overrides):
    values = dict(
        format_id="customer-standard-answer-v1",
        format_version="1.0",
        response_format="STANDARD",
        audiences=("CUSTOMER",),
        response_statuses=("ANSWER", "ANSWER_WITH_LIMITATIONS"),
        section_order=("DIRECT_ANSWER", "EXPLANATION", "CONDITION", "LIMITATION", "EVIDENCE"),
        allowed_section_types=("DIRECT_ANSWER", "EXPLANATION", "CONDITION", "LIMITATION", "EVIDENCE"),
        direct_answer_policy="REQUIRED",
        evidence_policy="WHEN_AVAILABLE",
        limitation_policy="REQUIRED_WHEN_PRESENT",
        clarification_policy="FORBIDDEN",
        priority=10,
    )
    values.update(overrides)
    return rr.build_format_definition(**values)


def _clarification(**overrides):
    values = dict(
        format_id="customer-clarification-v1",
        format_version="1.0",
        response_format="STANDARD",
        audiences=("CUSTOMER",),
        response_statuses=("CLARIFICATION_REQUIRED",),
        section_order=("CLARIFICATION",),
        allowed_section_types=("CLARIFICATION",),
        direct_answer_policy="FORBIDDEN",
        evidence_policy="FORBIDDEN",
        limitation_policy="FORBIDDEN",
        assumption_policy="FORBIDDEN",
        clarification_policy="REQUIRED",
        priority=20,
    )
    values.update(overrides)
    return rr.build_format_definition(**values)


def test_build_answer_definition():
    value = _answer()
    assert value.response_format == "STANDARD"
    assert value.registry_key == ("customer-standard-answer-v1", "1.0")


def test_definition_is_frozen():
    value = _answer()
    with pytest.raises(FrozenInstanceError):
        value.priority = 5  # type: ignore[misc]


def test_rejects_empty_audiences():
    with pytest.raises(rr.ResponseRegistryError, match="must not be empty"):
        _answer(audiences=())


def test_rejects_unknown_audience():
    with pytest.raises(rr.ResponseRegistryError, match="audiences"):
        _answer(audiences=("PUBLIC",))


def test_rejects_unknown_response_status():
    with pytest.raises(rr.ResponseRegistryError, match="response_statuses"):
        _answer(response_statuses=("UNKNOWN",))


def test_rejects_unknown_section_type():
    with pytest.raises(rr.ResponseRegistryError, match="allowed_section_types"):
        _answer(allowed_section_types=("UNKNOWN",))


def test_rejects_duplicate_section_order():
    with pytest.raises(rr.ResponseRegistryError, match="unique"):
        _answer(section_order=("EXPLANATION", "EXPLANATION"))


def test_section_order_must_be_allowed():
    with pytest.raises(rr.ResponseRegistryError, match="allowed section types"):
        _answer(section_order=("INTERNAL_NOTE",))


def test_rejects_nonpositive_word_limit():
    with pytest.raises(rr.ResponseRegistryError, match="positive integer"):
        _answer(max_section_words=0)


def test_rejects_boolean_word_limit():
    with pytest.raises(rr.ResponseRegistryError, match="positive integer"):
        _answer(max_sections=True)


def test_rejects_negative_priority():
    with pytest.raises(rr.ResponseRegistryError, match="non-negative"):
        _answer(priority=-1)


def test_answer_cannot_forbid_direct_answer():
    with pytest.raises(rr.ResponseRegistryError, match="cannot forbid direct answers"):
        _answer(direct_answer_policy="FORBIDDEN")


def test_answer_must_forbid_clarification():
    with pytest.raises(rr.ResponseRegistryError, match="forbid clarification"):
        _answer(clarification_policy="REQUIRED")


def test_answer_with_limitations_cannot_forbid_limitations():
    with pytest.raises(rr.ResponseRegistryError, match="cannot forbid limitations"):
        _answer(limitation_policy="FORBIDDEN")


def test_clarification_definition_is_valid():
    value = _clarification()
    assert value.clarification_policy == "REQUIRED"


def test_clarification_requires_clarification_policy():
    with pytest.raises(rr.ResponseRegistryError, match="require clarification"):
        _clarification(clarification_policy="FORBIDDEN")


def test_clarification_forbids_direct_answer():
    with pytest.raises(rr.ResponseRegistryError, match="forbid direct answers and evidence"):
        _clarification(direct_answer_policy="OPTIONAL")


def test_clarification_forbids_evidence():
    with pytest.raises(rr.ResponseRegistryError, match="forbid direct answers and evidence"):
        _clarification(evidence_policy="WHEN_AVAILABLE")


def test_clarification_allows_only_clarification_sections():
    with pytest.raises(rr.ResponseRegistryError, match="CLARIFICATION sections only"):
        _clarification(allowed_section_types=("CLARIFICATION", "LIMITATION"))


def test_registry_rejects_wrong_type():
    registry = rr.ResponseFormatRegistry()
    with pytest.raises(rr.ResponseRegistryError, match="ResponseFormatDefinition"):
        registry.register(object())  # type: ignore[arg-type]


def test_registry_rejects_exact_duplicate():
    item = _answer()
    registry = rr.ResponseFormatRegistry((item,))
    with pytest.raises(rr.ResponseRegistryError, match="duplicate response format"):
        registry.register(item)


def test_registry_rejects_same_id_different_version():
    registry = rr.ResponseFormatRegistry((_answer(),))
    with pytest.raises(rr.ResponseRegistryError, match="ambiguous duplicate format_id"):
        registry.register(_answer(format_version="2.0"))


def test_all_formats_are_deterministically_ordered():
    registry = rr.ResponseFormatRegistry((_clarification(priority=20), _answer(priority=10)))
    assert [item.format_id for item in registry.all_formats()] == [
        "customer-standard-answer-v1",
        "customer-clarification-v1",
    ]


def test_eligible_formats_match_all_dimensions():
    registry = rr.ResponseFormatRegistry((_answer(), _clarification()))
    eligible = registry.eligible_formats(response_format="STANDARD", audience="CUSTOMER", response_status="ANSWER")
    assert eligible == (_answer(),)
    assert registry.eligible_formats(response_format="COMPACT", audience="CUSTOMER", response_status="ANSWER") == ()


def test_select_one_returns_best_priority():
    first = _answer(format_id="first", priority=10)
    second = _answer(format_id="second", priority=20)
    registry = rr.ResponseFormatRegistry((second, first))
    assert registry.select_one(response_format="STANDARD", audience="CUSTOMER", response_status="ANSWER") == first


def test_select_one_rejects_no_match():
    registry = rr.ResponseFormatRegistry((_answer(),))
    with pytest.raises(rr.ResponseRegistryError, match="no eligible"):
        registry.select_one(response_format="STANDARD", audience="ADVISOR", response_status="ANSWER")


def test_select_one_rejects_same_priority_ambiguity():
    first = _answer(format_id="first", priority=10)
    second = _answer(format_id="second", priority=10)
    registry = rr.ResponseFormatRegistry((first, second))
    with pytest.raises(rr.ResponseRegistryError, match="ambiguous eligible"):
        registry.select_one(response_format="STANDARD", audience="CUSTOMER", response_status="ANSWER")
