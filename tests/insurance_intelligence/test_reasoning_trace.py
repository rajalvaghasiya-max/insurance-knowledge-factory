import pytest

from insurance_intelligence.contracts.reasoning import ReasoningContractError
from insurance_intelligence.reasoning.trace import ReasoningTraceBuilder


def test_trace_builder_assigns_ordered_sequences():
    builder = ReasoningTraceBuilder("trace-1")
    builder.add("REASONING_STARTED", "STARTED", "validated input received")
    builder.add("REASONING_COMPLETED", "COMPLETED", "reasoning aggregation completed")
    trace = builder.build()
    assert [event.sequence for event in trace] == [1, 2]
    assert [event.order_marker for event in trace] == ["event-0001", "event-0002"]


def test_trace_builder_preserves_trace_id():
    builder = ReasoningTraceBuilder("trace-abc")
    event = builder.add("REASONING_STARTED", "STARTED", "input received")
    assert event.trace_id == "trace-abc"


def test_trace_builder_preserves_structured_references():
    builder = ReasoningTraceBuilder("trace-1")
    event = builder.add(
        "RULE_EXECUTED",
        "EXECUTED",
        "registered deterministic rule completed",
        requirement_id="req-1",
        rule_id="rule-1",
        evidence_ids=("ev-2", "ev-1"),
        input_references=("context.trigger",),
        output_finding_ids=("finding-1",),
    )
    assert event.requirement_id == "req-1"
    assert event.rule_id == "rule-1"
    assert event.evidence_ids == ("ev-2", "ev-1")
    assert event.output_finding_ids == ("finding-1",)


def test_build_returns_immutable_snapshot():
    builder = ReasoningTraceBuilder("trace-1")
    builder.add("REASONING_STARTED", "STARTED", "input received")
    first = builder.build()
    builder.add("REASONING_COMPLETED", "COMPLETED", "done")
    assert len(first) == 1
    assert len(builder.build()) == 2


def test_invalid_event_type_fails_via_contract():
    builder = ReasoningTraceBuilder("trace-1")
    with pytest.raises(ReasoningContractError):
        builder.add("CHAIN_OF_THOUGHT", "NO", "not allowed")


def test_trace_contains_no_chain_of_thought_field():
    builder = ReasoningTraceBuilder("trace-1")
    event = builder.add("RULE_SELECTED", "SELECTED", "metadata matched")
    assert not hasattr(event, "chain_of_thought")
    assert not hasattr(event, "reasoning_text")


def test_trace_requires_nonempty_basis():
    builder = ReasoningTraceBuilder("trace-1")
    with pytest.raises(ReasoningContractError):
        builder.add("RULE_SELECTED", "SELECTED", "")


def test_trace_requires_nonempty_decision():
    builder = ReasoningTraceBuilder("trace-1")
    with pytest.raises(ReasoningContractError):
        builder.add("RULE_SELECTED", "", "metadata matched")


def test_trace_rejects_duplicate_evidence_ids():
    builder = ReasoningTraceBuilder("trace-1")
    with pytest.raises(ReasoningContractError):
        builder.add(
            "EVIDENCE_STATUS_CHECKED",
            "CHECKED",
            "evidence reviewed",
            evidence_ids=("ev-1", "ev-1"),
        )


def test_trace_event_is_frozen():
    builder = ReasoningTraceBuilder("trace-1")
    event = builder.add("REASONING_STARTED", "STARTED", "input received")
    with pytest.raises(Exception):
        event.sequence = 99
